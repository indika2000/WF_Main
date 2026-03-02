import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Generic hook for API data fetching.
 * Fetches on mount and provides refetch capability.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(() => getCart(userId));
 */
export function useApi<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (mountedRef.current) {
        setData(result);
      }
    } catch (err: any) {
      if (mountedRef.current) {
        setError(err?.message || "Request failed");
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetcher]);

  useEffect(() => {
    mountedRef.current = true;
    refetch();
    return () => {
      mountedRef.current = false;
    };
  }, [refetch]);

  return { data, loading, error, refetch };
}

/**
 * Generic hook for API mutations (POST, PATCH, DELETE).
 * Does NOT fetch on mount — only on explicit execute().
 *
 * Usage:
 *   const { execute, data, loading, error } = useMutation(
 *     (item: CartItemAdd) => addItem(userId, item)
 *   );
 *   await execute({ item_id: "pack-001", ... });
 */
export function useMutation<TResult, TArgs = void>(
  mutator: (args: TArgs) => Promise<TResult>
) {
  const [data, setData] = useState<TResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const execute = useCallback(
    async (args: TArgs): Promise<TResult> => {
      setLoading(true);
      setError(null);
      try {
        const result = await mutator(args);
        if (mountedRef.current) {
          setData(result);
        }
        return result;
      } catch (err: any) {
        const message = err?.message || "Request failed";
        if (mountedRef.current) {
          setError(message);
        }
        throw err;
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    },
    [mutator]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { execute, data, loading, error, reset };
}
