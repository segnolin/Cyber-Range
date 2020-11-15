var width = 2000;
var height = 2000;
var diameter = 10;
var gap = {
  text_width: 600,
  width: {
    0: 0,
    1: 400,
    2: 1000,
    3: 1400
  },
  height: 50
};
var margin = {
  top: 20,
  right: 160,
  bottom: 0,
  left: 160
};
var svg;
var nodes_list = [];
var nodes_dict = {};
var links = [];
var levelCount = 4;

var diagonal = d3.linkHorizontal().x(d => d.y).y(d => d.x);

function find(text) {
  return nodes_dict[text];
}

function mouseAction(val, stat, direction, steps, parent) {
  var temp = find(val.id);
  if (parent != "") (stat) ? temp.set.add(parent) : temp.set.delete(parent);
  if (steps > 0) {
    if (direction == "root") {
      temp.left.forEach(d => {
        (stat) ? temp.set.add(d) : temp.set.delete(d);
        d3.select("#l-" + val.id + "-" + d).classed("active-link", stat);
        d3.select("#l-" + d + "-" + val.id).classed("active-link", stat);
        d3.select("#l-" + val.id + "-" + d).classed("link", !stat);
        d3.select("#l-" + d + "-" + val.id).classed("link", !stat);
        mouseAction(find(d), stat, "left", steps - 1, val.id);
      });
      temp.right.forEach(d => {
        (stat) ? temp.set.add(d) : temp.set.delete(d);
        d3.select("#l-" + val.id + "-" + d).classed("active-link", stat);
        d3.select("#l-" + d + "-" + val.id).classed("active-link", stat);
        d3.select("#l-" + val.id + "-" + d).classed("link", !stat);
        d3.select("#l-" + d + "-" + val.id).classed("link", !stat);
        mouseAction(find(d), stat, "right", steps - 1, val.id);
      });
    }
    else if (direction == "left") {
      temp.left.forEach(d => {
        (stat) ? temp.set.add(d) : temp.set.delete(d);
        d3.select("#l-" + val.id + "-" + d).classed("active-link", stat);
        d3.select("#l-" + d + "-" + val.id).classed("active-link", stat);
        d3.select("#l-" + val.id + "-" + d).classed("link", !stat);
        d3.select("#l-" + d + "-" + val.id).classed("link", !stat);
        mouseAction(find(d), stat, direction, steps - 1, val.id);
      });
    }
    else if (direction == "right") {
      temp.right.forEach(d => {
        (stat) ? temp.set.add(d) : temp.set.delete(d);
        d3.select("#l-" + val.id + "-" + d).classed("active-link", stat);
        d3.select("#l-" + d + "-" + val.id).classed("active-link", stat);
        d3.select("#l-" + val.id + "-" + d).classed("link", !stat);
        d3.select("#l-" + d + "-" + val.id).classed("link", !stat);
        mouseAction(find(d), stat, direction, steps - 1, val.id);
      });
    }
  }
  if (temp.set.size == 0) {
    d3.select("#" + val.id).classed("active", stat);
  }
  else d3.select("#" + val.id).classed("active", true);
}

function wrap(text, width) {
  text.each(function() {
    var text = d3.select(this);
    var words = text.text().split(/\s+/).reverse(), word;
    var line = [];
    var lineNumber = 0;
    var lineHeight = 1.2;
    var x = text.attr("x");
    var y = text.attr("y");
    var dy = 1.2;
    var tspan = text.text(null).append("tspan")
      .attr("x", x)
      .attr("y", y)
      .attr("dy", dy + "em");
    while (word = words.pop()) {
      line.push(word);
      tspan.text(line.join(" "));
      if (tspan.node().getComputedTextLength() > width) {
        line.pop();
        tspan.text(line.join(" "));
        line = [word];
        lineNumber += 1;
        tspan = text.append("tspan")
          .attr("x", x)
          .attr("y", y)
          .attr("dy", lineNumber * lineHeight + dy + "em")
          .text(word)
      }
    }
  });
}

function renderGraph(data) {
  var count = [];
  var current = [];
  for (var i = 0; i < levelCount; i += 1) {
    count[i] = 0;
    current[i] = 0;
  }

  data.nodes.forEach(d => count[d.level] += 1);

  data.nodes.forEach((d, i) => {
    d.x = margin.left + d.level * diameter + gap.width[d.level];
    d.y = margin.top + (diameter + gap.height) * (current[d.level] + (Math.max.apply(Math, count) - count[d.level]) / 2);
    current[d.level] += 1;
    nodes_list.push(d);
    nodes_dict[d.id] = d;
    nodes_dict[d.id].left = [];
    nodes_dict[d.id].right = [];
    nodes_dict[d.id].set = new Set();
  });

  data.links.forEach(d => {
    links.push({
      source: find(d.source),
      target: find(d.target),
      id: "l-" + find(d.source).id + "-" + find(d.target).id
    });
    if (find(d.source).level > find(d.target).level) {
      find(d.source).left.push(d.target);
      find(d.target).right.push(d.source);
    }
    else {
      find(d.source).right.push(d.target);
      find(d.target).left.push(d.source);
    }
  });

  links.forEach(d => {
    svg.append("path", "g")
      .attr("class", "link")
      .attr("id", d.id)
      .attr("d", () => {
        var os = {
          x: d.source.y + diameter / 2,
          y: d.source.x
        };
        var ot = {
          x: d.target.y + diameter / 2,
          y: d.target.x
        };
        return diagonal({
          source: os,
          target: ot
        });
      });
  });

  svg.append("g")
    .attr("class", "nodes");

  var node = svg.select(".nodes")
    .selectAll("g")
    .data(nodes_list)
    .enter()
    .append("g")
    .attr("class", "unit");

  node.append("rect")
    .attr("x", d => { return d.x; })
    .attr("y", d => { return d.y; })
    .attr("id", d => { return d.id; })
    .attr("width", diameter)
    .attr("height", diameter)
    .attr("class", "node")
    .attr("rx", diameter / 2)
    .attr("ry", diameter / 2)
    .on("click", function() {
      mouseAction(d3.select(this).datum(), true, "root", d3.select("#step").node().value, "");
    })
    .on("contextmenu", function() {
      mouseAction(d3.select(this).datum(), false, "root", d3.select("#step").node().value, "");
      event.preventDefault();
    });

  node.append("text")
    .attr("class", "label")
    .attr("x", d => { return (d.level % 2) ? d.x + 20 : d.x - 20 + diameter; })
    .attr("y", d => { return d.y - diameter / 2; })
    .attr("dominant-baseline", "central")
    .attr("font-size", 15)
    .attr("font-family", "sans-serif")
    .attr("text-anchor", d => (d.level % 2) ? "start" : "end")
    .text(d => { return d.name; })
    .on("click", function() {
      mouseAction(d3.select(this).datum(), true, "root", d3.select("#step").node().value, "");
    })
    .on("contextmenu", function() {
      mouseAction(d3.select(this).datum(), false, "root", d3.select("#step").node().value, "");
      event.preventDefault();
    })
    .call(wrap, gap.text_width / 2)
    .clone(true).lower()
    .attr("stroke-linejoin", "round")
    .attr("stroke-width", 5)
    .attr("stroke", "white");
}

svg = d3.select("#tree").append("svg")
  .attr("width", width)
  .attr("height", height)
  .append("g");

renderGraph(data);
