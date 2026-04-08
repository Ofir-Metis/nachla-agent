"""Async Claude API wrapper with agentic tool-use loop.

Provides structured access to Claude for three tasks:
1. Document analysis — extract building data from parsed PDFs
2. Building classification — classify buildings using domain rules
3. Report narrative — generate professional Hebrew text

All arithmetic stays in deterministic Python tools. Claude never does math.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import anthropic

from agent.audit_log import AuditLogger
from config.settings import AppSettings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM interaction fails after all retries."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class LLMClient:
    """Async Claude API wrapper with tool-use loop and token tracking.

    Attributes:
        token_usage: Accumulated token usage across all calls in this session.
    """

    def __init__(self, settings: AppSettings, audit_logger: AuditLogger | None = None) -> None:
        settings.validate_anthropic_config()
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            max_retries=2,
        )
        self._model_main = settings.anthropic_model_main
        self._model_complex = settings.anthropic_model_complex
        self._max_retries = settings.max_tool_retries
        self._audit_logger = audit_logger
        self._token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
        }
        logger.info(
            "LLMClient initialized (main=%s, complex=%s)",
            self._model_main,
            self._model_complex,
        )

    @property
    def token_usage(self) -> dict[str, int]:
        """Accumulated token usage across all calls."""
        return dict(self._token_usage)

    def estimate_cost(self) -> dict[str, float]:
        """Estimate API cost from accumulated token usage.

        Uses approximate pricing for Sonnet and Opus blended.
        Sonnet: $3/M input, $15/M output. Opus: $15/M input, $75/M output.
        We estimate blended (mostly Sonnet): $5/M input, $25/M output.
        """
        input_cost = (self._token_usage["input_tokens"] / 1_000_000) * 5
        output_cost = (self._token_usage["output_tokens"] / 1_000_000) * 25
        return {
            "input_tokens": self._token_usage["input_tokens"],
            "output_tokens": self._token_usage["output_tokens"],
            "input_cost_usd": round(input_cost, 4),
            "output_cost_usd": round(output_cost, 4),
            "total_cost_usd": round(input_cost + output_cost, 4),
        }

    def _track_usage(self, response: anthropic.types.Message) -> None:
        """Accumulate token usage from a response."""
        self._token_usage["input_tokens"] += response.usage.input_tokens
        self._token_usage["output_tokens"] += response.usage.output_tokens

    def _log_llm_call(self, task: str, model: str, response: anthropic.types.Message, prompt_summary: str, response_summary: str) -> None:
        """Log an LLM call to the audit trail if logger is attached."""
        if self._audit_logger:
            self._audit_logger.log_llm_call(
                task=task,
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                prompt_summary=prompt_summary[:200],
                response_summary=response_summary[:200],
            )

    @staticmethod
    def _extract_text(content: list[Any]) -> str:
        """Extract text from response content blocks."""
        parts = []
        for block in content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)

    async def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 8192,
    ) -> anthropic.types.Message:
        """Single Claude API call with retry and token tracking.

        Args:
            system: System prompt.
            messages: Conversation messages.
            tools: Tool definitions (Anthropic format).
            model: Model override (defaults to main model).
            max_tokens: Maximum output tokens.

        Returns:
            The Claude Message response.

        Raises:
            LLMError: After all retries exhausted.
        """
        model = model or self._model_main
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = await self._client.messages.create(**kwargs)
                self._track_usage(response)
                return response
            except anthropic.RateLimitError as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning("Rate limited (attempt %d/%d), waiting %ds", attempt + 1, self._max_retries, wait)
                await asyncio.sleep(wait)
            except anthropic.APIConnectionError as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning("API connection error (attempt %d/%d): %s", attempt + 1, self._max_retries, e)
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                raise LLMError(f"Claude API error: {e}", original_error=e) from e

        raise LLMError(
            f"Claude API failed after {self._max_retries} retries",
            original_error=last_error,
        )

    async def agentic_loop(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor: Callable[..., Any],
        model: str | None = None,
        max_turns: int = 25,
        task_name: str = "agentic_loop",
    ) -> str:
        """Run a multi-turn agentic tool-use loop until Claude produces a final response.

        Args:
            system: System prompt.
            messages: Initial conversation messages (modified in place).
            tools: Tool definitions.
            tool_executor: Async callable (tool_name, inputs) -> result dict.
            model: Model override.
            max_turns: Safety limit on iterations.
            task_name: Name for audit logging.

        Returns:
            Final text response from Claude.

        Raises:
            LLMError: On API failure or max turns exceeded.
        """
        for turn in range(max_turns):
            response = await self.complete(system, messages, tools, model)

            # Append assistant response to message history
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final_text = self._extract_text(response.content)
                self._log_llm_call(
                    task=task_name,
                    model=model or self._model_main,
                    response=response,
                    prompt_summary=f"Agentic loop completed in {turn + 1} turns",
                    response_summary=final_text[:200],
                )
                return final_text

            # Execute tool calls
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = await tool_executor(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
                except Exception as e:
                    logger.error("Tool %s failed: %s", block.name, e)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            messages.append({"role": "user", "content": tool_results})

        raise LLMError(f"Agentic loop exceeded {max_turns} turns without completing")

    async def analyze_document(
        self,
        system: str,
        document_text: str,
        document_tables: list[list[list[str]]],
        extraction_prompt: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Extract structured data from a parsed document using Claude.

        Args:
            system: System prompt with domain knowledge.
            document_text: Full extracted text from PDF.
            document_tables: Tables extracted from PDF.
            extraction_prompt: Instructions for what to extract.
            model: Model override (defaults to main/Sonnet).

        Returns:
            Extracted data as a dict.
        """
        tables_text = ""
        if document_tables:
            for i, table in enumerate(document_tables):
                rows = [" | ".join(row) for row in table]
                tables_text += f"\n--- Table {i + 1} ---\n" + "\n".join(rows)

        user_content = (
            f"{extraction_prompt}\n\n"
            f"--- Document Text ---\n{document_text[:80000]}\n"  # Cap at ~80K chars
            f"{tables_text}\n\n"
            "Return your answer as a valid JSON object. No markdown fences."
        )

        messages = [{"role": "user", "content": user_content}]
        response = await self.complete(system, messages, model=model or self._model_main)
        text = self._extract_text(response.content)

        self._log_llm_call(
            task="document_analysis",
            model=model or self._model_main,
            response=response,
            prompt_summary=f"Document extraction ({len(document_text)} chars)",
            response_summary=text[:200],
        )

        # Parse JSON from response
        try:
            # Strip markdown fences if Claude adds them despite instructions
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Retry once asking for valid JSON
            logger.warning("Document analysis returned invalid JSON, retrying with nudge")
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": "That was not valid JSON. Please return ONLY a valid JSON object, no extra text.",
            })
            retry_response = await self.complete(system, messages, model=model or self._model_main)
            retry_text = self._extract_text(retry_response.content).strip()
            if retry_text.startswith("```"):
                retry_text = retry_text.split("\n", 1)[1] if "\n" in retry_text else retry_text[3:]
                if retry_text.endswith("```"):
                    retry_text = retry_text[:-3]
                retry_text = retry_text.strip()
            try:
                return json.loads(retry_text)
            except json.JSONDecodeError as e:
                logger.error("Document analysis JSON parse failed after retry: %s", e)
                return {"error": str(e), "raw_response": retry_text[:500]}

    async def classify_buildings(
        self,
        system: str,
        buildings_raw: list[dict[str, Any]],
        document_context: str,
        tools: list[dict[str, Any]],
        tool_executor: Callable[..., Any],
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """Classify buildings using Claude with domain knowledge and lookup tools.

        Args:
            system: System prompt with classification rules.
            buildings_raw: Raw building data dicts.
            document_context: Text from parsed documents for context.
            tools: Lookup tools (NOT calculation tools).
            tool_executor: Async callable for tool execution.
            model: Model override (defaults to complex/Opus).

        Returns:
            List of building dicts with updated building_type, status, and reasoning.
        """
        user_content = (
            "Classify each building according to the classification rules in your instructions.\n"
            "For each building, determine:\n"
            "1. building_type (one of: residential, service, agricultural, plach, pergola, pool, "
            "basement_service, basement_residential, attic, ground_floor_open, ground_floor_closed, "
            "temporary, shed_open, pre_1965)\n"
            "2. status (one of: compliant, deviation, no_permit, marked_demolition, building_line_violation)\n"
            "3. reasoning (Hebrew explanation of why this classification was chosen)\n\n"
            f"--- Buildings Data ---\n{json.dumps(buildings_raw, ensure_ascii=False, indent=2)}\n\n"
            f"--- Document Context ---\n{document_context[:30000]}\n\n"
            "After analysis, return a JSON array of objects with fields: "
            "id, building_type, status, reasoning. "
            "Use the lookup tools if you need priority area or rate information."
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
        result_text = await self.agentic_loop(
            system=system,
            messages=messages,
            tools=tools,
            tool_executor=tool_executor,
            model=model or self._model_complex,
            task_name="classification",
        )

        # Parse the classification results
        try:
            cleaned = result_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "buildings" in parsed:
                return parsed["buildings"]
            return [parsed]
        except json.JSONDecodeError:
            logger.error("Classification response was not valid JSON")
            return []

    async def generate_narrative(
        self,
        system: str,
        context: dict[str, Any],
        section_prompt: str,
        model: str | None = None,
    ) -> str:
        """Generate professional Hebrew narrative text for a report section.

        Args:
            system: System prompt.
            context: Report data context for the narrative.
            section_prompt: Instructions for what to write.
            model: Model override (defaults to main/Sonnet).

        Returns:
            Generated Hebrew text.
        """
        user_content = (
            f"{section_prompt}\n\n"
            f"--- Context Data ---\n{json.dumps(context, ensure_ascii=False, indent=2, default=str)}"
        )

        messages = [{"role": "user", "content": user_content}]
        response = await self.complete(system, messages, model=model or self._model_main)
        text = self._extract_text(response.content)

        self._log_llm_call(
            task="narrative",
            model=model or self._model_main,
            response=response,
            prompt_summary=f"Narrative: {section_prompt[:100]}",
            response_summary=text[:200],
        )

        return text
