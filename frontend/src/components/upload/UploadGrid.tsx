import UploadSlot from "./UploadSlot";

interface UploadGridProps {
  files: Record<string, File | null>;
  onFileChange: (id: string, file: File | null) => void;
}

export default function UploadGrid({ files, onFileChange }: UploadGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
      <UploadSlot
        id="survey_map"
        icon="&#x1F5FA;&#xFE0F;"
        label="מפת מדידה"
        formats="PDF, תמונה (JPG, PNG, TIFF)"
        required
        file={files.survey_map ?? null}
        onFileChange={onFileChange}
      />
      <UploadSlot
        id="building_permits"
        icon="&#x1F4C4;"
        label="היתרי בנייה"
        formats="PDF, תמונה (JPG, PNG, TIFF)"
        required
        file={files.building_permits ?? null}
        onFileChange={onFileChange}
      />
    </div>
  );
}
