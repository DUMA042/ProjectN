import { useEffect } from "react";
import { useToast } from "@/components/ui/Toast";
import { DOWNLOAD_ERROR_EVENT } from "@/lib/download";

/** Turns download failures into a user-visible toast. */
export default function DownloadErrorListener() {
  const { toast } = useToast();

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      toast(detail || "The file could not be saved.", "error");
    };
    window.addEventListener(DOWNLOAD_ERROR_EVENT, handler);
    return () => window.removeEventListener(DOWNLOAD_ERROR_EVENT, handler);
  }, [toast]);

  return null;
}
