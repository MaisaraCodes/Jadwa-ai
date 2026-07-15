// Sun/moon dark-mode toggle for portal headers. Reads/toggles the global
// ThemeProvider context.
import { IconMoon, IconSun } from "@tabler/icons-react";
import { useTheme } from "../lib/theme";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button
      type="button"
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      onClick={toggle}
      className="flex h-[31px] w-[31px] items-center justify-center rounded-lg border border-line-strong text-text-2 hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      {theme === "dark" ? <IconSun size={15} aria-hidden="true" /> : <IconMoon size={15} aria-hidden="true" />}
    </button>
  );
}
