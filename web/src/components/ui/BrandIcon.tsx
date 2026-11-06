import { siDocker, siFastapi, siGithub, siNumpy, siPandas, siPython, siScipy, siVultr } from "simple-icons";

const ICONS = {
  vultr: siVultr,
  docker: siDocker,
  python: siPython,
  pandas: siPandas,
  scipy: siScipy,
  numpy: siNumpy,
  fastapi: siFastapi,
  github: siGithub,
} as const;

export type BrandName = keyof typeof ICONS;

type Props = {
  name: BrandName;
  size?: number;
  mono?: boolean;
  className?: string;
};

/** A real brand mark in its own colour (from simple-icons), never a drawn look-alike. */
export function BrandIcon({ name, size = 20, mono = false, className }: Props) {
  const icon = ICONS[name];
  return (
    <svg
      role="img"
      aria-label={icon.title}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      fill={mono ? "currentColor" : `#${icon.hex}`}
    >
      <path d={icon.path} />
    </svg>
  );
}
