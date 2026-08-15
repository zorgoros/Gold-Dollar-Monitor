import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LocaleProvider, useLocale } from "./LocaleProvider.jsx";

function Probe() {
  const { copy, direction } = useLocale();
  return <span>{copy.app.name}|{direction}</span>;
}

describe("LocaleProvider", () => {
  it("provides English copy and LTR direction", () => {
    render(<LocaleProvider language="en"><Probe /></LocaleProvider>);

    expect(screen.getByText("Ayar Market|ltr")).toBeInTheDocument();
  });

  it("falls back to Persian for an unknown locale", () => {
    render(<LocaleProvider language="unknown"><Probe /></LocaleProvider>);

    expect(screen.getByText("عیار مارکت|rtl")).toBeInTheDocument();
  });
});
