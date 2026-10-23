import { useEffect, useState } from 'react'

export type Loaded<T> = { data: T | null; error: string | null; loading: boolean }

// Runs `load` whenever `key` changes and reports { data, error, loading }.
export function useFetch<T>(load: () => Promise<T>, key: string): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ data: null, error: null, loading: true })
  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    load()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e: Error) => !cancelled && setState({ data: null, error: e.message, loading: false }))
    return () => {
      cancelled = true
    }
    // `load` is a new function every render; `key` says when the request really changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return state
}
