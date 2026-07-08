/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
