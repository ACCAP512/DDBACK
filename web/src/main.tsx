import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./broker/broker.css";
import BrokerApp from "./broker/BrokerApp";

const el = document.getElementById("root");
if (!el) throw new Error("root element not found");

createRoot(el).render(
  <StrictMode>
    <BrokerApp />
  </StrictMode>,
);
