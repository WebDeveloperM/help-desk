import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          className={cn(
            "relative z-10 flex h-11 w-full appearance-none rounded-xl border border-input bg-background px-3.5 py-2 pr-9 text-[15px] text-foreground",
            "transition-colors focus-visible:border-accent focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-accent/20",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "[&>option]:bg-background [&>option]:text-foreground",
            className
          )}
          ref={ref}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 pointer-events-none text-muted-foreground" />
      </div>
    )
  }
)
Select.displayName = "Select"

export { Select }
