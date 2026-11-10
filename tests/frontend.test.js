const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const { runInNewContext } = require("node:vm");

const source = readFileSync(`${__dirname}/../src/static/app.js`, "utf8");

class Element {
  constructor() {
    this.children = [];
    this.options = this.children;
    this.listeners = {};
    this.value = "";
    this.classList = { add() {}, remove() {} };
  }

  set innerHTML(value) {
    this.html = value;
    this.children.length = 0;
  }

  appendChild(child) {
    this.children.push(child);
  }

  setAttribute() {}

  addEventListener(event, callback) {
    this.listeners[event] = callback;
  }
}

function activity(participants) {
  return {
    description: "Activity",
    schedule: "Friday",
    max_participants: 12,
    participants,
  };
}

function response(data) {
  return { ok: true, json: async () => data };
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

async function setup() {
  const elements = Object.fromEntries(
    ["activities-list", "activity", "signup-form", "message", "email"].map(
      (id) => [id, new Element()]
    )
  );
  elements.activity.appendChild(new Element());
  elements["signup-form"].reset = () => {
    elements.activity.value = "";
    elements.email.value = "";
  };
  const initial = {
    Chess: activity(["existing@school.edu"]),
    Art: activity([]),
  };
  const calls = [];
  const errors = [];
  let nextActivities = async () => response(initial);
  runInNewContext(source, {
    document: {
      getElementById: (id) => elements[id],
      createElement: () => new Element(),
      addEventListener: (event, callback) => callback(),
    },
    fetch: async (url, options) => {
      calls.push({ url, options });
      return options?.method
        ? response({ message: "Success" })
        : nextActivities();
    },
    console: { error: (...args) => errors.push(args) },
    setTimeout() {},
  });
  await flush();
  return {
    elements,
    calls,
    errors,
    setActivities: (handler) => { nextActivities = handler; },
    submit: () => elements["signup-form"].listeners.submit({ preventDefault() {} }),
    deleteFirst: () =>
      elements["activities-list"].children[0].children[0]
        .children[1].children[0].children[1].listeners.click(),
  };
}

function assertRegistered(elements) {
  const card = elements["activities-list"].children[1];
  assert.ok(card.html.includes("11 spots left"));
  const section = card.children[0];
  assert.equal(section.children[0].textContent, "Participantes (1)");
  const participant = section.children[1].children[0];
  assert.equal(participant.children[0].textContent, "new@school.edu");
  assert.equal(participant.children[1].className, "delete-participant");
  assert.equal(elements.activity.options.length, 3);
}

test("signup updates participants and availability without reloading", async () => {
  const app = await setup();
  app.setActivities(async () => response({
    Chess: activity(["existing@school.edu"]),
    Art: activity(["new@school.edu"]),
  }));
  app.elements.activity.value = "Art";
  app.elements.email.value = "new@school.edu";
  await app.submit();

  assertRegistered(app.elements);
  assert.equal(app.elements.activity.value, "");
  assert.equal(app.elements.message.className, "success");
  assert.equal(app.calls[1].options.method, "POST");
});

for (const staleFailure of [false, true]) {
  test(`older ${staleFailure ? "failed" : "successful"} refresh cannot undo signup`, async () => {
    const app = await setup();
    let finishOlderRequest;
    app.setActivities(() => new Promise((resolve, reject) => {
      finishOlderRequest = () => staleFailure
        ? reject(new Error("Older request failed"))
        : resolve(response({ Chess: activity([]), Art: activity([]) }));
    }));
    const deletion = app.deleteFirst();
    await flush();

    app.setActivities(async () => response({
      Chess: activity([]),
      Art: activity(["new@school.edu"]),
    }));
    app.elements.activity.value = "Art";
    app.elements.email.value = "new@school.edu";
    await app.submit();
    assertRegistered(app.elements);

    finishOlderRequest();
    await deletion;
    assertRegistered(app.elements);
  });
}

test("activity reads bypass cached data", async () => {
  const app = await setup();
  assert.equal(app.calls[0].options.cache, "no-store");
});
