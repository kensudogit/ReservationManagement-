"use client";

import { Suspense } from "react";
import SettingsContent from "./SettingsContent";

export default function SettingsPage() {
  return (
    <Suspense fallback={<p style={{ color: "var(--muted)" }}>読み込み中…</p>}>
      <SettingsContent />
    </Suspense>
  );
}
