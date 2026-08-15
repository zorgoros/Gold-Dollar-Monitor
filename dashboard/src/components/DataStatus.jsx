import { Pulse } from "@phosphor-icons/react";
import { formatTime } from "../format.js";
import { HelpTarget } from "./HelpSystem.jsx";

const STATUS = {
  LIVE: { label: "داده جاری", tone: "live" },
  LAST_CLOSE: { label: "آخرین بسته‌شدن", tone: "close" },
  STALE: { label: "داده قدیمی", tone: "stale" },
};

export function DataStatus({ status, fallbackAt }) {
  const meta = STATUS[status?.code] ?? STATUS.STALE;
  return (
    <HelpTarget
      className={`data-status data-status--${meta.tone}`}
      title="وضعیت داده"
      body="این نشان، تازگی داده را بررسی می‌کند. این نشان ساعت رسمی باز یا بسته بودن بازار نیست. داده جاری در محدوده تازگی تنظیم‌شده است؛ داده قدیمی از آن محدوده عبور کرده است."
    >
      <span className="status-dot" />
      <div><strong>{meta.label}</strong><small>آخرین داده {formatTime(status?.as_of ?? fallbackAt)}</small></div>
      <Pulse weight="duotone" />
    </HelpTarget>
  );
}
