import { Button } from "@acme/ui/button";
import { ArrowLeftIcon, Share2Icon } from "@acme/ui/icons";

export function Header({
  title,
  onBack,
  onShare,
}: {
  title: string;
  onBack: () => void;
  onShare: () => void;
}) {
  return (
    <header className="dark:bg-background fixed top-0 right-0 left-0 z-50 bg-white shadow-md">
      <div className="flex h-16 items-center gap-3 px-4">
        <Button
          size="icon"
          variant="ghost"
          aria-label="返回"
          className="text-foreground hover:bg-muted h-9 w-9 rounded-lg transition-colors"
          onClick={onBack}
        >
          <ArrowLeftIcon />
        </Button>
        <h1 className="text-foreground text-lg font-semibold">{title}</h1>
        <div className="flex-1" />
        <Button
          size="icon"
          variant="ghost"
          aria-label="分享"
          className="text-foreground hover:bg-muted h-9 w-9 rounded-lg transition-colors"
          onClick={onShare}
        >
          <Share2Icon />
        </Button>
      </div>
    </header>
  );
}
