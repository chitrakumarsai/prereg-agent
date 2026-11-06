import { BreakIt } from "@/components/console/BreakIt";
import { Containment } from "@/components/containment/Containment";
import { Hero } from "@/components/hero/Hero";
import { Footer } from "@/components/site/Footer";
import { Nav } from "@/components/site/Nav";
import { Workspace } from "@/components/workspace/Workspace";

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Workspace />
        <Containment />
        <BreakIt />
      </main>
      <Footer />
    </>
  );
}
