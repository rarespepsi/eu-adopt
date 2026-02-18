// HOME Layout Measurement Script
// Run this in DevTools Console on HOME page

console.clear();
const px = n => Math.round(n) + "px";
const r = el => el ? el.getBoundingClientRect() : null;

const viewportW = window.innerWidth;
const viewportH = window.innerHeight;

const A1 = document.querySelector("#A1");
const A2 = document.querySelector("#A2");
const left = document.querySelector("#A6")?.closest(".sidebar-left") || 
             document.querySelector(".sidebar-left") || null;
const right = document.querySelector("#A12")?.closest(".sidebar-right") || 
              document.querySelector(".sidebar-right") || null;
const center = A1?.closest(".main-content") || 
               document.querySelector(".main-content") || null;
const wrapper = center?.parentElement || 
                document.querySelector("#main_content .layout") || null;

function logBox(name, el){
  if(!el){ console.log(name + ": NOT FOUND"); return; }
  const b = r(el);
  const cs = getComputedStyle(el);
  console.log(name, {
    w: px(b.width), 
    h: px(b.height),
    ml: cs.marginLeft, 
    mr: cs.marginRight,
    pl: cs.paddingLeft, 
    pr: cs.paddingRight,
    display: cs.display, 
    position: cs.position,
    left: px(b.left),
    right: px(b.right)
  });
}

console.log("=== HOME LAYOUT MEASUREMENT ===");
console.log("Viewport:", viewportW+"px × "+viewportH+"px");
console.log("");

logBox("WRAPPER (.layout)", wrapper);
logBox("LEFT (.sidebar-left)", left);
logBox("CENTER (.main-content)", center);
logBox("RIGHT (.sidebar-right)", right);
logBox("A1", A1);
logBox("A2", A2);

// Calculate sum
if (left && center && right) {
  const leftW = r(left).width;
  const centerW = r(center).width;
  const rightW = r(right).width;
  const wrapperW = wrapper ? r(wrapper).width : 0;
  const sum = leftW + centerW + rightW;
  
  console.log("");
  console.log("=== CALCULATION ===");
  console.log("Left width:", px(leftW));
  console.log("Center width:", px(centerW));
  console.log("Right width:", px(rightW));
  console.log("Sum (left + center + right):", px(sum));
  console.log("Wrapper width:", px(wrapperW));
  console.log("Difference:", px(wrapperW - sum));
  console.log("Viewport width:", px(viewportW));
}
