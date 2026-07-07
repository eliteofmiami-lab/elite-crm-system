import "./globals.css";

export const metadata = {
  title: "Elite CRM — Painel",
  description: "Fila de trabalho e placar — Elite Premium Detailing",
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
