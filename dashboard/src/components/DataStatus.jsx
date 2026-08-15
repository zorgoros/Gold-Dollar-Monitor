import { Pulse } from "@phosphor-icons/react";
import { formatTime } from "../format.js";
import { HelpTarget } from "./HelpSystem.jsx";
import { useLocale } from "./LocaleProvider.jsx";

const STATUS = {
  LIVE: { tone: "live" },
  LAST_CLOSE: { tone: "close" },
  STALE: { tone: "stale" },
};

export function DataStatus({ status, fallbackAt }) {
  const { copy, language } = useLocale();
  const meta = STATUS[status?.code] ?? STATUS.STALE;
  const code = STATUS[status?.code] ? status.code : "STALE";
  const help = (
    <div className="status-help-list">
      <p><i className="status-swatch status-swatch--live" />{copy.status.liveHelp}</p>
      <p><i className="status-swatch status-swatch--close" />{copy.status.closeHelp}</p>
      <p><i className="status-swatch status-swatch--stale" />{copy.status.staleHelp}</p>
      <small>{copy.status.notCalendar}</small>
    </div>
  );
  return (
    <HelpTarget
      className={`data-status data-status--${meta.tone}`}
      title={copy.status.helpTitle}
      body={help}
    >
      <span className="status-dot" />
      <div><strong>{copy.status[code]}</strong><small>{copy.status.lastData} {formatTime(status?.as_of ?? fallbackAt, language)}</small></div>
      <Pulse weight="duotone" />
    </HelpTarget>
  );
}
