import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./tokens.css";
import "./index.css";
import { initTheme } from "./lib/theme";
import { initLang } from "./i18n/LangProvider";

initTheme();
initLang();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
