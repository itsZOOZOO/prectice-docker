/** Matches legacy lib/compress-profile-photo.ts */
const JPEG_QUALITY = 0.7
const MAX_DIMENSION = 1280

function imageToJpegBlob(
  source: HTMLImageElement,
  width: number,
  height: number
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const scale = Math.min(1, MAX_DIMENSION / Math.max(width, height))
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Could not get canvas context')
  ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new Error('Failed to encode JPEG'))
        else resolve(blob)
      },
      'image/jpeg',
      JPEG_QUALITY
    )
  })
}

/** Always compress profile photos: max 1280 side, JPEG @ 0.7 */
export async function compressProfilePhoto(file: File): Promise<File> {
  const url = URL.createObjectURL(file)
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = () => reject(new Error('Could not load image'))
      img.src = url
    })
    const blob = await imageToJpegBlob(image, image.naturalWidth, image.naturalHeight)
    const base = file.name.replace(/\.[^/.]+$/, '') || 'photo'
    return new File([blob], `${base}.jpg`, { type: 'image/jpeg' })
  } finally {
    URL.revokeObjectURL(url)
  }
}
