(() => {
  "use strict";

  const MAX_MESSAGE_LENGTH = 500;
  const MAX_HISTORY_MESSAGES = 10;

  const state = {
    aiPlan: null,
    aiRate: null,
    aiHistory: [],
    isSending: false,
    contactSending: false,
    toastTimer: null,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const api = {
    async postJson(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = data.error || "Something went wrong";
        const error = new Error(message);
        error.payload = data;
        error.status = response.status;
        throw error;
      }

      return data;
    },
  };

  const ui = {
    showToast(message, isError = false) {
      const toast = $("#toast");
      if (!toast) return;

      toast.textContent = message;
      toast.classList.toggle("error", isError);
      toast.classList.add("show");

      window.clearTimeout(state.toastTimer);
      state.toastTimer = window.setTimeout(() => {
        toast.classList.remove("show", "error");
      }, 3000);
    },

    initCursor() {
      const cursor = $("#cursor");
      const ring = $("#cursor-ring");
      if (!cursor || !ring) return;

      const prefersTouch = window.matchMedia("(pointer: coarse)").matches;
      const smallScreen = window.matchMedia("(max-width: 768px)").matches;
      if (prefersTouch || smallScreen) {
        document.body.classList.add("native-cursor");
        cursor.hidden = true;
        ring.hidden = true;
        return;
      }

      document.addEventListener("mousemove", (event) => {
        cursor.style.left = `${event.clientX}px`;
        cursor.style.top = `${event.clientY}px`;

        window.setTimeout(() => {
          ring.style.left = `${event.clientX}px`;
          ring.style.top = `${event.clientY}px`;
        }, 80);
      });
    },

    initReveal() {
      const revealItems = $$(".reveal");
      if (!revealItems.length) return;

      if (!("IntersectionObserver" in window)) {
        revealItems.forEach((item) => item.classList.add("visible"));
        return;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12 }
      );

      revealItems.forEach((item) => observer.observe(item));
    },

    scrollMessages() {
      const container = $("#aiMessages");
      if (!container) return;

      requestAnimationFrame(() => {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth",
        });
      });
    },

    setChatLoading(isLoading) {
      const input = $("#aiInput");
      const sendButton = $("#aiSend");
      const chips = $$(".ai-chip");

      state.isSending = isLoading;
      if (input) input.disabled = isLoading;
      if (sendButton) sendButton.disabled = isLoading;
      chips.forEach((chip) => {
        chip.disabled = isLoading;
      });
    },

    setFieldError(input, message) {
      const group = input.closest(".field-group");
      const errorEl = group ? $(".field-error", group) : null;

      input.classList.toggle("error", Boolean(message));
      if (errorEl) {
        errorEl.textContent = message || "";
        errorEl.classList.toggle("show", Boolean(message));
      }
    },

    clearFormErrors(form) {
      $$(".field-error", form).forEach((el) => {
        el.textContent = "";
        el.classList.remove("show");
      });
      $$(".error", form).forEach((el) => el.classList.remove("error"));
    },
  };

  const chat = {
    init() {
      const input = $("#aiInput");
      const sendButton = $("#aiSend");
      if (!input || !sendButton || !$("#aiMessages")) return;

      sendButton.addEventListener("click", () => chat.send());
      input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.shiftKey) return;
        event.preventDefault();
        chat.send();
      });

      input.addEventListener("input", () => {
        if (input.value.length > MAX_MESSAGE_LENGTH) {
          input.value = input.value.slice(0, MAX_MESSAGE_LENGTH);
          ui.showToast(`Messages are limited to ${MAX_MESSAGE_LENGTH} characters.`, true);
        }
      });

      $$(".ai-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          input.value = chip.dataset.text || chip.textContent || "";
          input.focus();
          chat.send();
        });
      });

      chat.addMessage(
        "assistant",
        "Hi! I'm your Pencil Insurance assistant. Select your plan above, then ask me anything: lost items, coverage questions, or how to file a claim."
      );
    },

    setPlan(name, rate) {
      state.aiPlan = name || null;
      state.aiRate = rate || null;

      $$(".plan-pill").forEach((pill) => {
        pill.classList.toggle("active", pill.dataset.plan === name);
      });
    },

    trimHistory(messages) {
      const trimmed = messages.slice(-MAX_HISTORY_MESSAGES);
      while (trimmed.length && trimmed[0].role !== "user") {
        trimmed.shift();
      }
      return trimmed;
    },

    addMessage(role, text) {
      const container = $("#aiMessages");
      if (!container) return;

      const isUser = role === "user";
      const row = document.createElement("div");
      row.className = `ai-msg${isUser ? " user" : ""}`;

      const avatar = document.createElement("div");
      avatar.className = `ai-avatar ${isUser ? "user" : "bot"}`;
      avatar.textContent = isUser ? "ME" : "PI";

      const bubble = document.createElement("div");
      bubble.className = `ai-bubble ${isUser ? "user" : "bot"}`;
      bubble.textContent = text;

      row.append(avatar, bubble);
      container.appendChild(row);
      ui.scrollMessages();
    },

    showTyping() {
      chat.removeTyping();

      const container = $("#aiMessages");
      if (!container) return;

      const row = document.createElement("div");
      row.className = "ai-msg";
      row.id = "typing";

      const avatar = document.createElement("div");
      avatar.className = "ai-avatar bot";
      avatar.textContent = "PI";

      const bubble = document.createElement("div");
      bubble.className = "ai-bubble bot";

      const dots = document.createElement("div");
      dots.className = "typing-dots";
      for (let index = 0; index < 3; index += 1) {
        dots.appendChild(document.createElement("span"));
      }

      bubble.appendChild(dots);
      row.append(avatar, bubble);
      container.appendChild(row);
      ui.scrollMessages();
    },

    removeTyping() {
      const typing = $("#typing");
      if (typing) typing.remove();
    },

    async send() {
      if (state.isSending) return;

      const input = $("#aiInput");
      if (!input) return;

      const text = input.value.trim();
      if (!text) return;

      if (text.length > MAX_MESSAGE_LENGTH) {
        ui.showToast(`Messages are limited to ${MAX_MESSAGE_LENGTH} characters.`, true);
        return;
      }

      input.value = "";
      chat.addMessage("user", text);

      state.aiHistory.push({ role: "user", content: text });
      state.aiHistory = chat.trimHistory(state.aiHistory);

      ui.setChatLoading(true);
      chat.showTyping();

      try {
        const data = await api.postJson("/api/chat", {
          messages: state.aiHistory,
          plan: state.aiPlan,
        });

        const reply = data.reply || "Sorry, something went wrong. Please contact us and we will help.";
        chat.addMessage("assistant", reply);
        state.aiHistory.push({ role: "assistant", content: reply });
        state.aiHistory = chat.trimHistory(state.aiHistory);
      } catch (error) {
        const fallbackMessage =
          error.status === 429
            ? "You have sent a few messages quickly, so I am pausing for a minute to protect the service. Please wait about 60 seconds and try again."
            : "I could not reach the assistant right now, but I can still help you get started. For urgent claims, email pencil.insurance.buisness@gmail.com or WhatsApp +91 98765 43210.";
        chat.addMessage("assistant", fallbackMessage);
        state.aiHistory.push({ role: "assistant", content: fallbackMessage });
        state.aiHistory = chat.trimHistory(state.aiHistory);
      } finally {
        chat.removeTyping();
        ui.setChatLoading(false);
        input.focus();
        ui.scrollMessages();
      }
    },
  };

  const contact = {
    init() {
      const form = $("#contactForm");
      if (!form) return;

      $$("input[required], textarea[required]", form).forEach((input) => {
        input.addEventListener("blur", () => contact.validateField(input));
        input.addEventListener("input", () => {
          if (input.classList.contains("error")) contact.validateField(input);
        });
      });

      form.addEventListener("submit", contact.submit);
    },

    validateEmail(email) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    validateField(input) {
      const value = input.value.trim();
      let error = "";

      if (input.name === "name" && value.length < 2) {
        error = "Name is required.";
      }

      if (input.name === "email" && !contact.validateEmail(value)) {
        error = "Enter a valid email address.";
      }

      if (input.name === "message" && value.length < 10) {
        error = "Message must be at least 10 characters.";
      }

      ui.setFieldError(input, error);
      return !error;
    },

    async submit(event) {
      event.preventDefault();

      if (state.contactSending) return;

      const form = event.currentTarget;
      const submitButton = $("button[type='submit']", form);
      const originalText = submitButton ? submitButton.textContent : "";

      let isValid = true;
      $$("input[required], textarea[required]", form).forEach((input) => {
        if (!contact.validateField(input)) isValid = false;
      });

      if (!isValid) {
        ui.showToast("Please fix the form and try again.", true);
        return;
      }

      state.contactSending = true;
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Sending...";
      }

      try {
        const formData = new FormData(form);
        await api.postJson("/api/contact", {
          name: formData.get("name"),
          email: formData.get("email"),
          plan: formData.get("plan"),
          message: formData.get("message"),
        });

        ui.showToast("Message sent. We'll reply within 24 hours.");
        form.reset();
        ui.clearFormErrors(form);
      } catch (error) {
        if (error.payload && error.payload.errors) {
          Object.entries(error.payload.errors).forEach(([field, message]) => {
            const input = $(`[name="${field}"]`, form);
            if (input) ui.setFieldError(input, message);
          });
        }
        ui.showToast("Please check the form and try again.", true);
      } finally {
        state.contactSending = false;
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = originalText;
        }
      }
    },
  };

  const plans = {
    init() {
      $$(".plan-btn").forEach((button) => {
        button.addEventListener("click", () => {
          const plan = button.dataset.plan;
          const rate = button.dataset.price;
          plans.select(plan, rate);
          ui.showToast(`${plan} plan selected.`);
        });
      });

      $$(".plan-pill").forEach((button) => {
        button.addEventListener("click", () => {
          chat.setPlan(button.dataset.plan, button.dataset.rate);
          ui.showToast(`Plan set to ${button.dataset.plan}.`);
        });
      });
    },

    select(plan, rate) {
      if (!plan) return;

      const contactPlan = $("#contactPlan");
      if (contactPlan) {
        const option = Array.from(contactPlan.options).find((item) =>
          item.textContent.toLowerCase().includes(plan.toLowerCase())
        );
        if (option) contactPlan.value = option.value;
      }

      chat.setPlan(plan, rate);
    },
  };

  const faq = {
    init() {
      $$(".faq-q").forEach((button) => {
        button.addEventListener("click", () => {
          const item = button.closest(".faq-item");
          const isOpen = item && item.classList.contains("open");

          $$(".faq-item").forEach((faqItem) => {
            faqItem.classList.remove("open");
            const faqButton = $(".faq-q", faqItem);
            if (faqButton) faqButton.setAttribute("aria-expanded", "false");
          });

          if (item && !isOpen) {
            item.classList.add("open");
            button.setAttribute("aria-expanded", "true");
          }
        });
      });
    },
  };

  const init = () => {
    ui.initCursor();
    ui.initReveal();
    faq.init();
    plans.init();
    chat.init();
    contact.init();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
