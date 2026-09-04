/** Max width before resize — matches legacy client-view / compress-image.ts */
const MAX_IMAGE_WIDTH = 1920
const WEBP_QUALITY = 0.8
const RESIZE_QUALITY = 0.9

function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = () => reject(new Error('Failed to load image'))
      img.src = e.target?.result as string
    }
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
  type: string,
  quality?: number
): Promise<Blob | null> {
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), type, quality)
  })
}

/**
 * Compress images before upload — same rules as legacy Next.js.
 * - Resize to max 1920px width
 * - Prefer WebP at 0.8 quality when smaller than original
 * - Else resized original type at 0.9, or original file if no benefit
 */
export async function compressImage(file: File): Promise<File> {
  const originalSize = file.size
  const img = await loadImageFromFile(file)

  let width = img.width
  let height = img.height
  if (width > MAX_IMAGE_WIDTH) {
    height = (height * MAX_IMAGE_WIDTH) / width
    width = MAX_IMAGE_WIDTH
  }

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return file
  ctx.drawImage(img, 0, 0, width, height)

  const webpBlob = await canvasToBlob(canvas, 'image/webp', WEBP_QUALITY)
  if (webpBlob && webpBlob.size < originalSize) {
    const fileName = file.name.replace(/\.[^/.]+$/, '') + '.webp'
    return new File([webpBlob], fileName, { type: 'image/webp' })
  }

  if (width < img.width) {
    const resizedBlob = await canvasToBlob(canvas, file.type || 'image/jpeg', RESIZE_QUALITY)
    if (resizedBlob) {
      return new File([resizedBlob], file.name, { type: file.type || 'image/jpeg' })
    }
  }

  return file
}
