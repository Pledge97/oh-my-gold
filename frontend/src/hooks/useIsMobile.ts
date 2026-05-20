import { useState, useEffect } from 'react'

/** 屏幕宽度断点，≤ 此值时视为手机端。 */
const MOBILE_BREAKPOINT = 768

/**
 * 监听窗口宽度，返回当前是否为手机端。
 *
 * @returns 当 window.innerWidth ≤ 768 时为 true。
 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth <= MOBILE_BREAKPOINT)

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  return isMobile
}
