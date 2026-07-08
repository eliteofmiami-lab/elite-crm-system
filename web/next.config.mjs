/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Carimbo do build: cliente e servidor do MESMO deploy compartilham o valor.
  // O delta devolve o do servidor; aba com bundle antigo detecta e recarrega
  // sozinha (fim do "F5 manual" toda vez que sai deploy).
  env: { NEXT_PUBLIC_BUILD: String(Date.now()) },
  // MVP: painel embutível DENTRO do GHL (Custom Menu Link abre em iframe).
  // frame-ancestors libera só o GHL + o próprio painel.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self' https://app.gohighlevel.com https://*.gohighlevel.com https://app.eliteofmiami.com;",
          },
        ],
      },
    ];
  },
};
export default nextConfig;
