import { useEffect, useState } from "react";

export function PhotoPicker({ photos, onAdd, onRemove, disabled = false }) {
  const [previews, setPreviews] = useState([]);

  useEffect(() => {
    const urls = photos.map((file) => URL.createObjectURL(file));
    setPreviews(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [photos]);

  return (
    <>
      <label className={`dropzone ${photos.length ? "has-photo" : ""}`}>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          disabled={disabled}
          onChange={(event) => {
            onAdd(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
        {photos.length ? (
          <>
            <span className="upload-symbol">＋</span>
            <b>Ajouter des photos</b>
            <small>
              {photos.length} photo{photos.length === 1 ? "" : "s"} sélectionnée
              {photos.length === 1 ? "" : "s"}
            </small>
          </>
        ) : (
          <>
            <span className="upload-symbol">＋</span>
            <b>Choisir une ou plusieurs photos</b>
            <small>JPG, PNG ou WebP</small>
          </>
        )}
      </label>
      {photos.length > 0 && (
        <div className="photo-previews" aria-label="Photos sélectionnées">
          {photos.map((photo, index) => (
            <figure
              className="photo-preview"
              key={`${photo.name}-${photo.lastModified}-${index}`}
            >
              <img src={previews[index]} alt={`Aperçu de ${photo.name}`} />
              <figcaption title={photo.name}>{photo.name}</figcaption>
              <button
                type="button"
                className="photo-remove"
                aria-label={`Retirer ${photo.name}`}
                disabled={disabled}
                onClick={() => onRemove(index)}
              >
                ×
              </button>
            </figure>
          ))}
        </div>
      )}
    </>
  );
}
