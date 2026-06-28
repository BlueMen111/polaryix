import { redirect } from "next/navigation";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ slug: "placeholder" }];
}

export default function LegacyPublicPage() {
  redirect("/#converter");
}
