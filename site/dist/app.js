async function loadShowcase() {
  const response = await fetch("showcase.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Showcase data failed: ${response.status}`);
  return response.json();
}

function text(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value || "";
}

function render(data) {
  text("pair-label", data.label);
  text("demo-notice", data.demo_notice || "This is a curated, approved example.");
  text("post-text", data.draft.post_text);
  text("main-claim", data.draft.main_claim);
  text("alt-text", data.storyboard.alt_text);
  text("privacy-copy", data.privacy);
  const image = document.getElementById("motion-image");
  image.src = data.assets.gif;
  image.alt = data.storyboard.alt_text;

  const rules = document.getElementById("voice-rules");
  data.voice_rules.forEach((rule) => {
    const item = document.createElement("li");
    item.textContent = rule;
    rules.appendChild(item);
  });

  const frames = document.getElementById("storyboard-frames");
  data.storyboard.frames.forEach((frame, index) => {
    const article = document.createElement("article");
    article.className = "frame";
    article.innerHTML = `<span class="number">0${index + 1}</span><strong></strong><p></p><small></small>`;
    article.querySelector("strong").textContent = frame.on_screen_words;
    article.querySelector("p").textContent = frame.visual_change;
    article.querySelector("small").textContent = `${frame.duration_seconds.toFixed(1)}s · ${frame.transition}`;
    frames.appendChild(article);
  });
}

loadShowcase().then(render).catch((error) => {
  text("demo-notice", "The showcase data could not be loaded. The static fallback remains available.");
  console.error(error);
});

