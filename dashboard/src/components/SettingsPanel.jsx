import { useEffect, useState } from "react";
import { GearSix, X } from "@phosphor-icons/react";
import { useLocale } from "./LocaleProvider.jsx";

const STORAGE_KEY = "ayar-dashboard-settings-v1";
const DEFAULT_SETTINGS = {
  language: "fa",
  reduceMotion: false,
  chartTooltips: true,
  showCoin: true,
  showTable: true,
  highContrast: false,
};

export function useDashboardSettings() {
  const [settings, setSettings] = useState(() => {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(window.localStorage?.getItem(STORAGE_KEY) || "{}") };
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  useEffect(() => {
    try {
      window.localStorage?.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Storage can be disabled by privacy settings. Controls still work for
      // the current session, so persistence is optional rather than fatal.
    }
    document.documentElement.dataset.reduceMotion = String(settings.reduceMotion);
    document.documentElement.dataset.contrast = settings.highContrast ? "high" : "standard";
  }, [settings]);

  const update = (name, value) => setSettings((current) => ({ ...current, [name]: value }));
  return [settings, update];
}

function Toggle({ name, label, checked, onChange }) {
  return (
    <label className="setting-row">
      <span>{label}</span>
      <input type="checkbox" name={name} checked={checked} onChange={(event) => onChange(name, event.target.checked)} />
    </label>
  );
}

export function SettingsButton({ onClick }) {
  const { copy } = useLocale();
  return <button className="icon-button" type="button" aria-label={copy.settings.button} title={copy.hints.settings} onClick={onClick}><GearSix /></button>;
}

export function SettingsPanel({ open, onClose, settings, onChange }) {
  const { copy } = useLocale();
  if (!open) return null;
  return (
    <aside className="settings-panel" role="dialog" aria-modal="true" aria-label={copy.settings.dialog}>
      <header>
        <div><p>{copy.settings.eyebrow}</p><h2>{copy.settings.title}</h2></div>
        <button type="button" className="dialog-close" aria-label={copy.settings.close} title={copy.hints.closeSettings} onClick={onClose}><X /></button>
      </header>
      <div className="settings-group">
        <h3>{copy.settings.tools}</h3>
        <Toggle name="chartTooltips" label={copy.settings.chartTooltips} checked={settings.chartTooltips} onChange={onChange} />
        <Toggle name="showCoin" label={copy.settings.showCoin} checked={settings.showCoin} onChange={onChange} />
        <Toggle name="showTable" label={copy.settings.showTable} checked={settings.showTable} onChange={onChange} />
      </div>
      <div className="settings-group">
        <h3>{copy.settings.accessibility}</h3>
        <Toggle name="reduceMotion" label={copy.settings.reduceMotion} checked={settings.reduceMotion} onChange={onChange} />
        <Toggle name="highContrast" label={copy.settings.highContrast} checked={settings.highContrast} onChange={onChange} />
      </div>
      <fieldset className="settings-language">
        <legend>{copy.settings.language}</legend>
        <label><input type="radio" name="language" value="fa" checked={settings.language === "fa"} onChange={() => onChange("language", "fa")} /> {copy.settings.persian}</label>
        <label><input type="radio" name="language" value="en" checked={settings.language === "en"} onChange={() => onChange("language", "en")} /> {copy.settings.english}</label>
      </fieldset>
    </aside>
  );
}
