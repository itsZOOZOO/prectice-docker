/** Crop/rotate/flip canvas helpers (port of prectice/lib/crop-image-canvas.ts). */

export type PixelCrop = {
  x: number
  y: number
  width: number
  height: number
  unit?: 'px'
}

const TO_RADIANS = Math.PI / 180

function createImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.crossOrigin = 'anonymous'
    image.addEventListener('load', () => resolve(image))
    image.addEventListener('error', error => reject(error))
    image.src = url
  })
}

/** Draw cropped region to canvas (from react-image-crop demo). */
export async function canvasPreview(
  image: HTMLImageElement,
  canvas: HTMLCanvasElement,
  crop: PixelCrop,
  scale = 1,
  rotate = 0,
  flipHorizontal = false,
  flipVertical = false
) {
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('No 2d context')

  const scaleX = image.naturalWidth / image.width
  const scaleY = image.naturalHeight / image.height
  const pixelRatio = window.devicePixelRatio || 1

  canvas.width = Math.floor(crop.width * scaleX * pixelRatio)
  canvas.height = Math.floor(crop.height * scaleY * pixelRatio)

  ctx.scale(pixelRatio, pixelRatio)
  ctx.imageSmoothingQuality = 'high'

  const cropX = crop.x * scaleX
  const cropY = crop.y * scaleY
  const rotateRads = rotate * TO_RADIANS
  const centerX = image.naturalWidth / 2
  const centerY = image.naturalHeight / 2
  const flipX = (flipHorizontal ? -1 : 1) * scale
  const flipY = (flipVertical ? -1 : 1) * scale

  ctx.save()
  ctx.translate(-cropX, -cropY)
  ctx.translate(centerX, centerY)
  ctx.rotate(rotateRads)
  ctx.scale(flipX, flipY)
  ctx.translate(-centerX, -centerY)
  ctx.drawImage(
    image,
    0,
    0,
    image.naturalWidth,
    image.naturalHeight,
    0,
    0,
    image.naturalWidth,
    image.naturalHeight
  )
  ctx.restore()
}

export async function getCroppedImageFile(
  image: HTMLImageElement,
  crop: PixelCrop,
  fileName: string,
  rotate = 0,
  flipHorizontal = false,
  flipVertical = false
): Promise<File | null> {
  const canvas = document.createElement('canvas')
  await canvasPreview(image, canvas, crop, 1, rotate, flipHorizontal, flipVertical)
  const blob = await new Promise<Blob | null>(resolve =>
    canvas.toBlob(resolve, 'image/jpeg', 0.9)
  )
  if (!blob) return null
  const base = fileName.replace(/\.[^.]+$/, '')
  return new File([blob], `${base}-cropped.jpg`, {
    type: 'image/jpeg',
    lastModified: Date.now()
  })
}

export async function canvasToJpegFile(
  canvas: HTMLCanvasElement,
  fileName: string,
  quality = 0.9
): Promise<File | null> {
  const blob = await new Promise<Blob | null>(resolve =>
    canvas.toBlob(resolve, 'image/jpeg', quality)
  )
  if (!blob) return null
  const base = fileName.replace(/\.[^.]+$/, '') || 'photo'
  return new File([blob], `${base}-cropped.jpg`, {
    type: 'image/jpeg',
    lastModified: Date.now()
  })
}

export async function fetchUrlAsFile(url: string, fileName = 'photo.jpg'): Promise<File> {
  const res = await fetch(url)
  if (!res.ok) throw new Error('Could not load photo')
  const blob = await res.blob()
  const type = blob.type || 'image/jpeg'
  const ext = type.includes('png') ? 'png' : type.includes('webp') ? 'webp' : 'jpg'
  const base = fileName.replace(/\.[^.]+$/, '') || 'photo'
  return new File([blob], `${base}.${ext}`, { type, lastModified: Date.now() })
}
