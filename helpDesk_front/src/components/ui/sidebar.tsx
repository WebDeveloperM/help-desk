"use client";

import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import React, { useState, createContext, useContext } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";

interface Links {
  label: string;
  href: string;
  icon: React.JSX.Element | React.ReactNode;
  count?: string | number;
}

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(
  undefined
);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
};

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);

  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  return (
    <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
      {children}
    </SidebarProvider>
  );
};

export const SidebarBody = (props: React.ComponentProps<typeof motion.div>) => {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...(props as React.ComponentProps<"div">)} />
    </>
  );
};

export const DesktopSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof motion.div>) => {
  const { open, setOpen, animate } = useSidebar();
  const sidebarWidth = animate ? (open ? 300 : 80) : 300;
  
  return (
    <motion.div
      className={cn(
        "fixed left-0 top-0 z-50 h-screen px-4 py-4 hidden md:flex md:flex-col bg-surface border-r border-border flex-shrink-0",
        className
      )}
      animate={{
        width: animate ? (open ? "300px" : "80px") : "300px",
      }}
      transition={{
        duration: 0.3,
        ease: "easeInOut",
      }}
      onMouseEnter={() => animate && setOpen(true)}
      onMouseLeave={() => animate && setOpen(false)}
      style={{
        ...(props.style as object),
        ['--sidebar-width' as string]: `${sidebarWidth}px`,
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export const MobileSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  const { open, setOpen } = useSidebar();
  return (
    <>
      <div
        className={cn(
          "h-14 px-4 py-4 flex flex-row md:hidden items-center justify-between bg-surface border-b border-border w-full fixed top-0 left-0 z-50"
        )}
        {...props}
      >
        <div className="flex justify-end z-20 w-full">
          <Menu
            className="text-text-primary cursor-pointer"
            onClick={() => setOpen(!open)}
            size={24}
          />
        </div>
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ x: "-100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "-100%", opacity: 0 }}
              transition={{
                duration: 0.3,
                ease: "easeInOut",
              }}
              className={cn(
                "fixed h-full w-full inset-0 bg-surface p-10 z-[100] flex flex-col justify-between",
                className
              )}
            >
              <div
                className="absolute right-10 top-10 z-50 text-text-primary cursor-pointer"
                onClick={() => setOpen(!open)}
              >
                <X size={24} />
              </div>
              {children}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
};

export const SidebarLink = ({
  link,
  active,
  onClick,
  className,
  ...props
}: {
  link: Links;
  active?: boolean;
  onClick?: () => void;
  className?: string;
  props?: React.ComponentProps<typeof Link>;
}) => {
  const { open, animate } = useSidebar();
  
  const handleClick = (_e: React.MouseEvent<HTMLAnchorElement>) => {
    onClick?.();
    // Don't prevent default - let React Router handle navigation
  };

  return (
    <Link
      to={link.href}
      onClick={handleClick}
      className={cn(
        "flex items-center justify-start gap-3 group/sidebar py-3 px-4 rounded-xl transition-all relative",
        active
          ? "bg-surfaceHover text-text-primary font-medium"
          : "text-text-secondary hover:bg-surfaceHover",
        // Center content when collapsed
        !open && animate && "justify-center px-2",
        className
      )}
      {...props}
    >
      <span className={cn(
        "flex-shrink-0 w-5 h-5 flex items-center justify-center text-current opacity-80 transition-all",
        // Add centered shadow when collapsed
        !open && animate && "shadow-lg shadow-black/10 dark:shadow-black/30"
      )}>
        {link.icon}
      </span>
      <motion.span
        animate={{
          display: animate ? (open ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (open ? 1 : 0) : 1,
          width: animate ? (open ? "auto" : 0) : "auto",
        }}
        transition={{ duration: 0.2 }}
        className="text-sm group-hover/sidebar:translate-x-1 transition duration-150 whitespace-nowrap overflow-hidden flex-1"
      >
        {link.label}
      </motion.span>
      {link.count && (
        <motion.span
          animate={{
            display: animate ? (open ? "inline-block" : "none") : "inline-block",
            opacity: animate ? (open ? 1 : 0) : 1,
          }}
          transition={{ duration: 0.2 }}
          className="text-xs text-text-tertiary bg-borderLight px-2 py-0.5 rounded-full flex-shrink-0"
        >
          {link.count}
        </motion.span>
      )}
    </Link>
  );
};

export const SidebarHeader = ({
  className,
  children,
  ...props
}: Omit<React.ComponentProps<typeof motion.div>, 'animate'>) => {
  const { open, animate } = useSidebar();
  return (
    <motion.div
      className={cn("mb-4", className)}
      animate={{
        opacity: animate ? (open ? 1 : 0.5) : 1,
      }}
      {...(props as any)}
    >
      {children}
    </motion.div>
  );
};

export const SidebarFooter = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  return (
    <div
      className={cn("mt-auto pt-6", className)}
      {...props}
    >
      {children}
    </div>
  );
};

export const SidebarSection = ({
  className,
  title,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  title?: string;
}) => {
  const { open, animate } = useSidebar();
  return (
    <div className={cn("mt-8", className)} {...props}>
      {title && (
        <motion.div
          className="text-xs font-medium text-text-tertiary px-4 mb-3"
          animate={{
            display: animate ? (open ? "block" : "none") : "block",
            opacity: animate ? (open ? 1 : 0) : 1,
          }}
        >
          {title}
        </motion.div>
      )}
      {children}
    </div>
  );
};
