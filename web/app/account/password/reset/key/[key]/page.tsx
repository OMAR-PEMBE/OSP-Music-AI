import { AuthScreen } from "@/components/auth-screen";

export default async function Page({
  params,
}: {
  params: Promise<{ key: string }>;
}) {
  const { key } = await params;
  return <AuthScreen mode="reset" token={decodeURIComponent(key)} />;
}
