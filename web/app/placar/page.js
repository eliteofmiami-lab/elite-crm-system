"use client";
import { useEffect } from "react";

// O placar agora vive na vista do dono (rota /). Redireciona.
export default function Placar() {
  useEffect(() => { window.location.href = "/"; }, []);
  return null;
}
