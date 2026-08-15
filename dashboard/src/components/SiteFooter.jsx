import { useHelp } from "./HelpSystem.jsx";
import { useLocale } from "./LocaleProvider.jsx";

export function SiteFooter({ asOf, onOpenSettings }) {
  const { setEnabled } = useHelp();
  const { copy } = useLocale();
  return (
    <footer className="site-footer">
      <div className="footer-brand"><strong>{copy.app.name}</strong><p>{copy.footer.description}</p></div>
      <nav aria-label={copy.footer.navLabel}>
        <button type="button" title={copy.hints.help} onClick={() => setEnabled(true)}>{copy.footer.help}</button>
        <button type="button" title={copy.hints.settings} onClick={onOpenSettings}>{copy.footer.settings}</button>
        <a href="https://github.com/zorgoros/Gold-Dollar-Monitor" target="_blank" rel="noreferrer">{copy.footer.docs}</a>
      </nav>
      <div className="footer-note"><span>{copy.footer.latest} {asOf}</span><p>{copy.footer.disclaimer}</p></div>
      <div className="footer-legal">
        <a href="https://mostahub.com" target="_blank" rel="noreferrer">{copy.footer.rights}</a>{" "}
        <span>{copy.footer.designedBy}</span>
      </div>
    </footer>
  );
}
