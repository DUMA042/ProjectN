import { describe, expect, it } from "vitest";
import { bytesToBase64, isDesktopApp } from "@/lib/tauri";

describe("desktop bridge", () => {
  it("encodes file bytes for the host command", () => {
    expect(bytesToBase64(new TextEncoder().encode("Flow"))).toBe("Rmxvdw==");
    expect(bytesToBase64(new Uint8Array())).toBe("");
  });

  it("detects a browser environment", () => {
    expect(isDesktopApp()).toBe(false);
  });
});
