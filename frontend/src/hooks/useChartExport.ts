import type { RefObject } from 'react'

function triggerDownload(url: string, filename: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
}

/**
 * Captures the first <svg> element found inside `containerRef` and exports it
 * as a PNG (rendered via Canvas) or as a standalone SVG file.
 */
export function useChartExport(containerRef: RefObject<HTMLElement | null>) {
  const exportAs = (format: 'png' | 'svg', filename: string): void => {
    const container = containerRef.current
    if (!container) return

    const svgEl = container.querySelector('svg')
    if (!svgEl) return

    // Clone and make self-contained
    const clone = svgEl.cloneNode(true) as SVGSVGElement
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    const { width, height } = svgEl.getBoundingClientRect()
    clone.setAttribute('width', String(width))
    clone.setAttribute('height', String(height))

    const svgString = new XMLSerializer().serializeToString(clone)
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const svgUrl = URL.createObjectURL(svgBlob)

    if (format === 'svg') {
      triggerDownload(svgUrl, `${filename}.svg`)
      URL.revokeObjectURL(svgUrl)
      return
    }

    // PNG: draw SVG onto a canvas, then export as PNG blob
    const img = new Image()
    img.onload = () => {
      const scale = window.devicePixelRatio ?? 1
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.scale(scale, scale)
      // White background suitable for reports
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, width, height)
      ctx.drawImage(img, 0, 0, width, height)
      URL.revokeObjectURL(svgUrl)
      canvas.toBlob((blob) => {
        if (!blob) return
        const pngUrl = URL.createObjectURL(blob)
        triggerDownload(pngUrl, `${filename}.png`)
        URL.revokeObjectURL(pngUrl)
      }, 'image/png')
    }
    img.src = svgUrl
  }

  return { exportAs }
}
