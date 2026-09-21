export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return <section className="content-card placeholder-page"><span className="welcome-kicker">EN CONSTRUCCIÓN</span><h2>{title}</h2><p>{description}</p></section>;
}
