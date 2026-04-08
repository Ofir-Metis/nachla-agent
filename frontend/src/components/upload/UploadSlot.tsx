import { useRef, useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

interface UploadSlotProps {
  id: string;
  label: string;
  icon: string;
  formats: string;
  required?: boolean;
  file: File | null;
  onFileChange: (id: string, file: File | null) => void;
  accept?: Record<string, string[]>;
}

export default function UploadSlot({
  id,
  label,
  icon,
  formats,
  required = false,
  file,
  onFileChange,
  accept,
}: UploadSlotProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const validate = useCallback((f: File): string | null => {
    if (f.size > MAX_SIZE) return `הקובץ גדול מדי (מקסימום 50MB)`;
    const ext = getExtension(f.name);
    if (!ALLOWED_EXTENSIONS.includes(ext))
      return `סוג קובץ לא נתמך (${ext}). נתמכים: PDF, PNG, JPG, TIFF`;
    return null;
  }, []);

  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length === 0) return;
      const f = accepted[0];
      const err = validate(f);
      setValidationError(err);
      if (!err) {
        onFileChange(id, f);
      } else {
        onFileChange(id, null);
      }
    },
    [id, onFileChange, validate],
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      multiple: false,
      accept: accept ?? {
        "application/pdf": [".pdf"],
        "image/png": [".png"],
        "image/jpeg": [".jpg", ".jpeg"],
        "image/tiff": [".tiff", ".tif"],
      },
      maxSize: MAX_SIZE,
    });

  const hasFile = file !== null;

  // Derive error from either our validation or dropzone rejections
  let error = validationError;
  if (!error && fileRejections.length > 0) {
    const rejection = fileRejections[0];
    if (rejection.errors.some((e) => e.code === "file-too-large")) {
      error = "הקובץ גדול מדי (מקסימום 50MB)";
    } else if (rejection.errors.some((e) => e.code === "file-invalid-type")) {
      error = "סוג קובץ לא נתמך. נתמכים: PDF, PNG, JPG, TIFF";
    } else {
      error = "שגיאה בהעלאת הקובץ";
    }
  }

  const handleCamera = (e: React.MouseEvent) => {
    e.stopPropagation();
    cameraRef.current?.click();
  };

  const handleCameraChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const err = validate(f);
    setValidationError(err);
    if (!err) {
      onFileChange(id, f);
    }
    e.target.value = "";
  };

  return (
    <div className="relative">
      <div
        {...getRootProps()}
        className={`p-4 sm:p-6 px-3 sm:px-4 border-2 border-dashed rounded-[--radius-md] sm:rounded-[--radius-lg] text-center cursor-pointer transition-all ${
          hasFile
            ? "border-solid border-olive-400 bg-olive-50"
            : isDragActive
              ? "border-olive-400 bg-olive-50"
              : "border-[#D8D0C4] bg-white hover:border-olive-400 hover:bg-olive-50"
        }`}
      >
        <input {...getInputProps()} />

        {required && (
          <span className="absolute top-2 right-2.5 text-[0.7rem] font-semibold text-terra-500 bg-terra-500/8 px-2 py-0.5 rounded-full">
            * חובה
          </span>
        )}

        {hasFile && (
          <span className="absolute top-2 start-2.5 w-6 h-6 rounded-full bg-success text-white flex items-center justify-center text-sm font-bold leading-none">
            &#10003;
          </span>
        )}

        <div className="text-[2rem] mb-2 leading-none">{icon}</div>
        <div className="font-semibold text-[0.9rem] text-soil-800 mb-1">{label}</div>
        <div className="text-[0.78rem] text-soil-500 mb-3">{formats}</div>

        {hasFile && file && (
          <div className="text-[0.8rem] text-olive-700 font-medium mb-2 break-all">
            {file.name}{" "}
            <span className="text-soil-500 font-normal" dir="ltr">
              ({formatFileSize(file.size)})
            </span>
          </div>
        )}

        <button
          type="button"
          onClick={handleCamera}
          className="text-[0.78rem] text-olive-600 bg-transparent border-none cursor-pointer hover:text-olive-800 transition-colors"
        >
          &#128247; צלם תמונה
        </button>

        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleCameraChange}
        />
      </div>

      {error && (
        <p role="alert" className="text-[0.78rem] text-error mt-1.5 px-1 font-medium">
          {error}
        </p>
      )}
    </div>
  );
}
