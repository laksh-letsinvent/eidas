export default function ComingSoon({
  eyebrow,
  title,
  arrives,
  children,
}: {
  eyebrow: string;
  title: string;
  arrives: string;
  children: React.ReactNode;
}) {
  return (
    <article>
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p className="lede">{children}</p>
      <div className="soon-tag">Arrives in {arrives}</div>
    </article>
  );
}
