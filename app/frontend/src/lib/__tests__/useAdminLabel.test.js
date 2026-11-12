import { renderHook } from "@testing-library/react";
import { useAdminLabel } from "@/lib/useAdminLabel";
import AppContextProvider from "@/context/AppContextProvider";

const wrapperWith = (appConfig) =>
  function Wrapper({ children }) {
    return (
      <AppContextProvider appConfig={appConfig}>{children}</AppContextProvider>
    );
  };

describe("useAdminLabel", () => {
  it("returns the admin label configured in appConfig", () => {
    const { result } = renderHook(() => useAdminLabel(), {
      wrapper: wrapperWith({
        admin_label: { one: "District", many: "Districts" },
      }),
    });
    expect(result.current).toEqual({ one: "District", many: "Districts" });
  });

  it("falls back to the Eswatini default when admin_label is unset", () => {
    const { result } = renderHook(() => useAdminLabel(), {
      wrapper: wrapperWith({}),
    });
    expect(result.current).toEqual({ one: "Inkhundla", many: "Tinkhundla" });
  });
});
