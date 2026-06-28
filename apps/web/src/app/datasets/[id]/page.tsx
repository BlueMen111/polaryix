import { redirect } from "next/navigation";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function DatasetDetailsPage() {
  redirect("/#converter");
}
