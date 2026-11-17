"use client";

import React, { useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function Tooltip({
     content,
     children,
     side = "top",
     delay = 300,
}: {
     content: React.ReactNode;
     children: React.ReactElement;
     side?: "top" | "bottom" | "left" | "right";
     delay?: number;
}) {
     const [visible, setVisible] = useState(false);
     const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

     const show = () => {
          timer.current = setTimeout(() => setVisible(true), delay);
     };
     const hide = () => {
          if (timer.current) clearTimeout(timer.current);
          setVisible(false);
     };

     const posClass =
          side === "top"
               ? "bottom-full mb-2 left-1/2 -translate-x-1/2"
               : side === "bottom"
                    ? "top-full mt-2 left-1/2 -translate-x-1/2"
                    : side === "left"
                         ? "right-full mr-2 top-1/2 -translate-y-1/2"
                         : "left-full ml-2 top-1/2 -translate-y-1/2";

     return (
          <span
               className="relative inline-flex"
               onMouseEnter={show}
               onMouseLeave={hide}
               onFocus={show}
               onBlur={hide}
          >
               {children}
               {visible && (
                    <span
                         role="tooltip"
                         className={cn(
                              "pointer-events-none absolute z-50 whitespace-nowrap rounded-md border border-border bg-inverse px-2.5 py-1 text-xs font-medium text-fg-inverse shadow-md animate-fade-in",
                              posClass
                         )}
                    >
                         {content}
                    </span>
               )}
          </span>
     );
}