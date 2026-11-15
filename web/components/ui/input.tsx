import * as React from "react";
import { cn } from "@/lib/utils";
export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 rounded-md border border-neutral-200 bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-neutral-300 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
