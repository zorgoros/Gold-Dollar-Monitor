import { useHelp } from "./HelpSystem.jsx";

export function SiteFooter({ asOf, onOpenSettings }) {
  const { setEnabled } = useHelp();
  return (
    <footer className="site-footer">
      <div className="footer-brand"><strong>عیار مارکت</strong><p>نمای مستقل داده و تحلیل بازار طلا و ارز</p></div>
      <nav aria-label="پیوندهای پایین صفحه">
        <button type="button" onClick={() => setEnabled(true)}>راهنمای تعاملی</button>
        <button type="button" onClick={onOpenSettings}>تنظیمات نمایش</button>
        <a href="https://github.com/zorgoros/Gold-Dollar-Monitor" target="_blank" rel="noreferrer">کد و مستندات</a>
      </nav>
      <div className="footer-note"><span>آخرین داده: {asOf}</span><p>این صفحه گزارش داده است و توصیه خرید یا فروش نیست.</p></div>
    </footer>
  );
}
