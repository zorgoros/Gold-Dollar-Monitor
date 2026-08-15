import { createContext, useContext, useMemo, useState } from "react";
import { Question, X } from "@phosphor-icons/react";
import { useLocale } from "./LocaleProvider.jsx";

const HelpContext = createContext(null);

export function HelpProvider({ children }) {
  const [enabled, setEnabled] = useState(false);
  const [topic, setTopic] = useState(null);
  const value = useMemo(
    () => ({ enabled, setEnabled, topic, setTopic }),
    [enabled, topic],
  );
  return <HelpContext.Provider value={value}>{children}</HelpContext.Provider>;
}

export function useHelp() {
  const context = useContext(HelpContext);
  if (!context) throw new Error("useHelp must be used inside HelpProvider");
  return context;
}

export function HelpToggle({ className = "icon-button" }) {
  const { enabled, setEnabled, setTopic } = useHelp();
  const { copy } = useLocale();
  const toggle = () => {
    setEnabled((current) => !current);
    setTopic(null);
  };
  return (
    <button
      className={`${className} ${enabled ? "is-active" : ""}`}
      type="button"
      aria-label={copy.help.pageLabel}
      title={copy.hints.help}
      aria-pressed={enabled}
      onClick={toggle}
    >
      <Question weight={enabled ? "fill" : "regular"} />
    </button>
  );
}

export function HelpTarget({ title, body, className = "", children }) {
  const { enabled, setTopic } = useHelp();
  const { copy } = useLocale();
  return (
    <div className={`help-target ${enabled ? "is-help-enabled" : ""} ${className}`}>
      {children}
      {enabled && (
        <button
          type="button"
          className="help-marker"
          aria-label={`${copy.help.targetPrefix} ${title}`}
          title={`${copy.help.targetPrefix} ${title}`}
          onClick={() => setTopic({ title, body })}
        >
          <Question weight="bold" />
        </button>
      )}
    </div>
  );
}

export function HelpDialog() {
  const { topic, setTopic } = useHelp();
  const { copy } = useLocale();
  if (!topic) return null;
  return (
    <section className="help-dialog" role="dialog" aria-modal="false" aria-label={topic.title}>
      <button type="button" className="dialog-close" aria-label={copy.help.close} title={copy.hints.closeHelp} onClick={() => setTopic(null)}>
        <X />
      </button>
      <p>{copy.help.section}</p>
      <h2>{topic.title}</h2>
      <div>{topic.body}</div>
    </section>
  );
}
