import { resolveTheme } from "@/lib/helper";
import { THEME_PRESETS, DEFAULT_THEME } from "@/static/config";

describe("resolveTheme", () => {
  it("returns the matching theme by name", () => {
    const teal = THEME_PRESETS.find((t) => t.name === "Teal");
    expect(resolveTheme("Teal")).toBe(teal);
  });

  it("falls back to the default theme for unknown or missing names", () => {
    expect(resolveTheme("Nope")).toBe(DEFAULT_THEME);
    expect(resolveTheme(undefined)).toBe(DEFAULT_THEME);
  });
});
