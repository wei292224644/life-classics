export default function CodeLayout(props: {
  children: React.ReactNode;
  params: Promise<{ code: string }>;
}) {
  return props.children;
}
