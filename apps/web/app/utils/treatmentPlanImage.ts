/** Treatment-plan photo resize/preview helpers (port of prectice/lib/treatment-plan-image.ts). */

import { compressImage } from '~/utils/compressImage'

export const MAX_TPLAN_PHOTOS_PER_ROW = 10
export const TPLAN_PHOTO_ACCEPT = 'image/*,.heic,.heif'

const IMAGE_EXTENSIONS = new Set([
  'jpg', 'jpeg', 'jpe', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp'
])

export function isImageFile(file: File): boolean {
  if (file.type.startsWith('image/')) return true
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  return IMAGE_EXTENSIONS.has(ext)
}

function isHeicOrHeif(file: File): boolean {
  const type = file.type.toLowerCase()
  if (type === 'image/heic' || type === 'image/heif') return true
  const ext = file.name.split('.').pop()?.toLowerCase() ?? ''
  return ext === 'heic' || ext === 'heif'
}

export async function resizeTreatmentPlanImage(file: File): Promise<File> {
  if (!isImageFile(file)) return file
  try {
    const compressed = await compressImage(file)
    if (!isHeicOrHeif(compressed)) return compressed
  } catch {
    // fall through
  }
  return file
}

export async function createTreatmentPlanPhotoPreview(file: File): Promise<string | null> {
  try {
    const resized = await resizeTreatmentPlanImage(file)
    return URL.createObjectURL(resized)
  } catch {
    try {
      return URL.createObjectURL(file)
    } catch {
      return null
    }
  }
}

/** Load any displayable image file as a data URL (for cropper). */
export async function loadImageDataUrlForCropper(file: File): Promise<string | null> {
  try {
    const resized = await resizeTreatmentPlanImage(file)
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = () => reject(new Error('Failed to read image'))
      reader.readAsDataURL(resized)
    })
  } catch {
    try {
      return await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result as string)
        reader.onerror = () => reject(new Error('Failed to read image'))
        reader.readAsDataURL(file)
      })
    } catch {
      return null
    }
  }
}

export function revokePhotoPreview(previewUrl: string | null | undefined) {
  if (previewUrl?.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl)
  }
}
