import { createRoot } from "react-dom/client";
import App from "./App";
import "./fonts.css";
import { applyLang } from "./i18n";
import { applyTheme, getMode, watchSystem } from "./theme";
import "./theme.css";

applyLang();
applyTheme(getMode());
watchSystem();
createRoot(document.getElementById("root")!).render(<App />);
