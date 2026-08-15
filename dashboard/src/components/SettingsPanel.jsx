import { useEffect, useState } from "react";
import { GearSix, X } from "@phosphor-icons/react";

const STORAGE_KEY = "ayar-dashboard-settings-v1";
const DEFAULT_SETTINGS = {
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
  return <button className="icon-button" type="button" aria-label="تنظیمات" onClick={onClick}><GearSix /></button>;
}

export function SettingsPanel({ open, onClose, settings, onChange }) {
  if (!open) return null;
  return (
    <aside className="settings-panel" role="dialog" aria-modal="true" aria-label="تنظیمات داشبورد">
      <header>
        <div><p>نمایش و دسترس‌پذیری</p><h2>تنظیمات</h2></div>
        <button type="button" className="dialog-close" aria-label="بستن تنظیمات" onClick={onClose}><X /></button>
      </header>
      <div className="settings-group">
        <h3>ابزارها</h3>
        <Toggle name="chartTooltips" label="راهنمای شناور نمودار" checked={settings.chartTooltips} onChange={onChange} />
        <Toggle name="showCoin" label="نمایش کارت سکه امامی" checked={settings.showCoin} onChange={onChange} />
        <Toggle name="showTable" label="نمایش جدول جزئیات" checked={settings.showTable} onChange={onChange} />
      </div>
      <div className="settings-group">
        <h3>دسترس‌پذیری</h3>
        <Toggle name="reduceMotion" label="کاهش حرکت" checked={settings.reduceMotion} onChange={onChange} />
        <Toggle name="highContrast" label="کنتراست بیشتر" checked={settings.highContrast} onChange={onChange} />
      </div>
      <div className="settings-language"><span>زبان</span><strong>فارسی</strong><small>English در نسخه بعد</small></div>
    </aside>
  );
}
