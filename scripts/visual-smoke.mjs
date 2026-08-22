import fs from "node:fs";

const [url, selector, output, widthText = "1440", heightText = "1000", action = "open"] = process.argv.slice(2);
if (!url || !selector || !output) throw new Error("Usage: node visual-smoke.mjs <url> <selector> <output> [width] [height]");

const target = await fetch(`http://127.0.0.1:9222/json/new?${encodeURIComponent(url)}`, { method: "PUT" }).then((response) => response.json());
const socket = new WebSocket(target.webSocketDebuggerUrl);
const pending = new Map();
let requestId = 0;

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.method === "Runtime.exceptionThrown") console.error("browser_exception", message.params?.exceptionDetails?.text, message.params?.exceptionDetails?.exception?.description || "");
  if (message.method === "Log.entryAdded") console.error("browser_log", message.params?.entry?.level, message.params?.entry?.text, message.params?.entry?.url || "");
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});
function command(method, params = {}) {
  const id = ++requestId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

await command("Page.enable");
await command("Runtime.enable");
await command("Log.enable");
await command("Emulation.setDeviceMetricsOverride", {
  width: Number(widthText),
  height: Number(heightText),
  deviceScaleFactor: 1,
  mobile: Number(widthText) <= 620,
});
await command("Page.navigate", { url });
await wait(2500);
const clicked = await command("Runtime.evaluate", {
  expression: `Boolean((element => element && (element.click(), true))(document.querySelector(${JSON.stringify(selector)})))`,
  returnByValue: true,
});
if (!clicked.result?.value) throw new Error(`Selector not found: ${selector}`);
await wait(2200);
const opened = await command("Runtime.evaluate", {
  expression: "Boolean(document.querySelector('.decision-drawer'))",
  returnByValue: true,
});
console.log(`drawer_open=${Boolean(opened.result?.value)}`);
if (action === "complete-plan" || action === "complete-plan-download") {
  async function reply(value) {
    await command("Runtime.evaluate", {
      expression: `(() => { const field = document.querySelector('.drawer-composer textarea'); const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; setter.call(field, ${JSON.stringify(value)}); field.dispatchEvent(new Event('input', { bubbles: true })); field.form.requestSubmit(); return true; })()`,
      returnByValue: true,
    });
    await wait(350);
  }
  await reply("I want the best relocation plan around Manchester");
  await reply("Manchester");
  await reply("300000");
  await command("Runtime.evaluate", {
    expression: `(() => { const priorities = [...document.querySelectorAll('.priority-conversation > div button')]; priorities.slice(0, 2).forEach(button => button.click()); document.querySelector('.priority-conversation > .button').click(); return true; })()`,
    returnByValue: true,
  });
  await wait(350);
  await reply("skip");
  await wait(9000);
  const reportReady = await command("Runtime.evaluate", { expression: "Boolean(document.querySelector('.drawer-report'))", returnByValue: true });
  console.log(`report_ready=${Boolean(reportReady.result?.value)}`);
  if (action === "complete-plan-download") {
    const downloadPath = `${process.cwd()}\\.visual-chrome\\downloads`;
    fs.mkdirSync(downloadPath, { recursive: true });
    await command("Browser.setDownloadBehavior", { behavior: "allow", downloadPath, eventsEnabled: true });
    await command("Runtime.evaluate", { expression: "document.querySelector('.report-actions .button').click()" });
    await wait(1200);
    console.log(`downloads=${fs.readdirSync(downloadPath).join(',')}`);
  }
}
const screenshot = await command("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
fs.writeFileSync(output, Buffer.from(screenshot.data, "base64"));
await command("Target.closeTarget", { targetId: target.id });
socket.close();
