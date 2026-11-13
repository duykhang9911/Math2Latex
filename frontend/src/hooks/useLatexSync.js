import { useEffect } from 'react'

/**
 * Syncs the MathLive mathfield element's value with the controlled `value` prop.
 * Call this inside FormulaEditor, passing the ref and the current value.
 * Catches errors from MathLive when it cannot parse the LaTeX.
 */
export function useMathfieldSync(mathfieldRef, value) {
  useEffect(() => {
    const field = mathfieldRef.current
    if (!field || field.value === value) return
    try {
      field.value = value
    } catch {
      // MathLive may throw on unparseable LaTeX — silently ignore
      // The textarea still shows the raw LaTeX and the user can edit it.
    }
  }, [mathfieldRef, value])
}
