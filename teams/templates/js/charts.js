google.load('visualization', '1', {packages: ['corechart', 'bar','table']});

google.setOnLoadCallback(drawStacked);

function drawStacked() {

//   Chart 1
//  var data1 = new google.visualization.DataTable();
//  data1.addColumn('string', 'Puzzle Name');
//  data1.addColumn('number', 'Solved');
//  data1.addColumn('number', 'Unlocked');
//  data1.addColumn('number', 'Locked');

//  data1.addRows([
//    {% for point in data1_list %}
//      ["{{point.name}}", {{point.solved}}, {{point.unlocked}}, {{point.locked}}],
//    {% endfor %}
//  ]);

//  var options1 = {
//    title: 'Puzzle solves',
//    isStacked: true,
//    height: 400,
//    width: 800,
//    chartArea: {
//       top: 20,
//       left: 100,
//       height: '50%',
//       width: 500
//    },
//    hAxis: {slantedText:true, slantedTextAngle:60 },
//  };

//  var chart1 = new google.visualization.ColumnChart(document.getElementById('chart_div1'));
//  chart1.draw(data1, options1);


//  // Chart 2
//  var data2 = new google.visualization.DataTable();
//  data2.addColumn('string', 'Puzzle Name');
//  data2.addColumn('number', 'Correct guesss');
//  data2.addColumn('number', 'Incorrect guesss');

//  data2.addRows([
//    {% for point in data2_list %}
//      ["{{point.name}}", {{point.correct}}, -{{point.incorrect}}],
//    {% endfor %}
//  ]);

//  var options2 = {
//    title: 'Puzzle guesss',
//    isStacked: true,
//    height: 500,
//    width: 800,
//    chartArea: {
//       top: 20,
//       left: 100,
//       height: 300,
//       width: 500
//    },
//    hAxis: {slantedText:true, slantedTextAngle:60 },
//  };

//  var chart2 = new google.visualization.ColumnChart(document.getElementById('chart_div2'));
//  chart2.draw(data2, options2);


//  var data7 = new google.visualization.DataTable();
//  data7.addColumn('string', 'Puzzle Name');
//  data7.addColumn('number', 'Number of Hints');

//  data7.addRows([
//    {% for point in data7_list %}
//      ["{{point.name}}", {{point.hints}}],
//    {% endfor %}
//  ]);

//  var options7 = {
//    title: 'Hints per Puzzle',
//    isStacked: true,
//    height: 400,
//    width: 800,
//    chartArea: {
//       top: 20,
//       left: 100,
//       height: '50%',
//       width: 500
//    },
//    hAxis: {slantedText:true, slantedTextAngle:60 },
//  };

//  var chart7 = new google.visualization.ColumnChart(document.getElementById('chart_div7'));
//  chart7.draw(data7, options7);


//  // Chart 3
//  var data3 = new google.visualization.DataTable();
//  data3.addColumn('string', 'Hour');
//  data3.addColumn('number', '# Guesss');

//  data3.addRows([
//    {% for point in data3_list %}
//      ["{{point.hour}}", {{point.amount}}],
//    {% endfor %}
//  ]);

//  var options3 = {
//    title: 'Guesss over time',
//    isStacked: true,
//    height: 400,
//    width: 800,
//    chartArea: {
//       top: 20,
//       left: 50,
//       height: '50%'
//    },
//    pointSize: 3,
//    hAxis: {slantedText:true, slantedTextAngle:60 },
//  };

//  var chart3 = new google.visualization.LineChart(document.getElementById('chart_div3'));
//  chart3.draw(data3, options3);


//  // Chart 4
//  var data4 = new google.visualization.DataTable();
//  data4.addColumn('string', 'Hour');
//  data4.addColumn('number', '# Solves');

//  data4.addRows([
//    {% for point in data4_list %}
//      ["{{point.hour}}", {{point.amount}}],
//    {% endfor %}
//  ]);

//  var options4 = {
//    title: 'Solves over time',
//    isStacked: true,
//    height: 400,
//    width: 800,
//    chartArea: {
//       top: 20,
//       left: 50,
//       height: '50%'
//    },
//    pointSize: 3,
//    hAxis: {slantedText:true, slantedTextAngle:60 },
//  };

//  var chart4 = new google.visualization.LineChart(document.getElementById('chart_div4'));
//  chart4.draw(data4, options4);



  // Chart 5
  
  
  var options5 = {
    title: 'Plot solutions over time (seconds)',
    isStacked: true,
    height: 400,
    width: 800,
    chartArea: {
       top: 20,
       left: 50,
       height: '50%'
    },
    pointSize: 3,
    hAxis: {slantedText:true, slantedTextAngle:60 },
  };
  
//  var data5 = new google.visualization.DataTable();
//    
//  data5.addColumn('date', 'Time');
//  data5.addColumn('number', '#solve');

//  data5.addRows(
//  [
//    {% for team in data5_list %}{% for point in team.solve %}
//      [new Date({{point.year}},{{point.month}},{{point.day}},{{point.hour}},{{point.minute}},{{point.second}}), {{forloop.counter}} ],
//    {% endfor %}{%endfor%}
//  ]
//  );
//  

//  var chart5 = new google.visualization.LineChart(document.getElementById('chart_div5'));
//  chart5.draw(data5, options5);
//  


// print progress per team
  
  var joind = new google.visualization.DataTable();
  joind.addColumn('date', 'Time');
  joind.addColumn('number', 'dummy');
  
  var columns=[];
  
  
  {% for team in data5_list %}
   var fdata{{forloop.counter}} = new google.visualization.DataTable();
    fdata{{forloop.counter}}.addColumn('date', 'Time');
    fdata{{forloop.counter}}.addColumn('number', '{{team.name|truncatechars:30}}');
    
    fdata{{forloop.counter}}.addRows(
  [
    {% for point in team.solve %}
      [new Date(Date.UTC({{point.year}},{{point.month}},{{point.day}},{{point.hour}},{{point.minute}},{{point.second}})), {{forloop.counter}} ],
    {%endfor%}
  ]
  );
    joind = google.visualization.data.join(joind, fdata{{forloop.counter}}, 'full', [[0, 0]], columns, [1]);
    columns.push({{forloop.counter}});
  {% endfor %}
    
    
    var chart5 = new google.visualization.LineChart(document.getElementById('chart_div5'));
    chart5.draw(joind, options5);
  
  
  
  
  
  
  
  
  
  
  var options_puz = {
    title: 'Puzzle solved time (minutes)',
    isStacked: true,
    height: 400,
    width: 800,
    chartArea: {
       top: 20,
       left: 50,
       height: '50%'
    },
    pointSize: 3,
    hAxis: {slantedText:true, slantedTextAngle:60 },
  };
  
  
  var data_puz = new google.visualization.DataTable();
  data_puz.addColumn('number', 'index');
  data_puz.addColumn('number', 'Min Time');
  data_puz.addColumn('number', 'Ave Time');
  
  var columns=[];
  
  
  data_puz.addRows(
  [
    {% for point in data_puz %}
    {% if point.min_dur == None %}
      [ {{forloop.counter}} , null, null ],
    {% else %}      
      [ {{forloop.counter}} , {{point.min_dur.seconds}}/60, {{point.av_dur.seconds}}/60 ],
    {%endif%}
    {%endfor%}
  ]
  );
    
    
    var chart_puz = new google.visualization.LineChart(document.getElementById('chart_div_puz'));
    chart_puz.draw(data_puz, options_puz);
  


  // Chart 5
/*  var data5 = new google.visualization.DataTable();
  data5.addColumn('datetime', 'Time');
  data5.addColumn('number', 'No solves');
  {% for puzzle in puzzles %}
    data5.addColumn('number', "{{puzzle.puzzle_name}} Solves");
  {% endfor %}


  data5.addRows([
    {% for line in data5_list %}
      [
        {% for point in line %}
          {% if forloop.first %}
            new Date("{{ point.isoformat }}"),
          {% else %}
            {{point|safe}},
          {% endif %}
        {% endfor %}
      ],
    {% endfor %}
  ]);

  var options5 = {
    title: 'Solves by team over time',
    height: 1000,
    width: 1200,
    chartArea: {
       top: 20,
       left: 50,
       height: '50%'
    },
    isStacked: true,
    //vAxis: {scaleType: "mirrorLog"},
    hAxis: {slantedText:true, slantedTextAngle:60 },
  };

  var chart5 = new google.visualization.AreaChart(document.getElementById('chart_div5'));
  chart5.draw(data5, options5);*/


  // Chart 6
/*  var data6 = new google.visualization.DataTable();
  data6.addColumn('number', 'Puzzle_id');
  data6.addColumn('number', 'Time to solve (Minutes)');

  data6.addRows([
    {% for point in data6_list %}
      [{{point.0|safe}}, {{point.1|safe}}],
    {% endfor %}
  ]);

  var options6 = {
    title: 'Solves by team over time',
    height: 1000,
    width: 1000,
    pointSize: 2,
    chartArea: {
       top: 20,
       left: 50,
       height: '90%',
       width: '80%'
    },
    //vAxis: {logScale: true}
  };

  var chart6 = new google.visualization.ScatterChart(document.getElementById('chart_div6'));
  chart6.draw(data6, options6);*/
}

/*window.onload = function () {

var options = {
  title: {
    text: "Solves by team over time",
    horizontalAlign: "left",
    //fontWeight: "lighter",
    fontFamily: "arial",
    fontSize: 15
  },
  axisX: {
    valueFormatString: "hh tt",
    labelFontSize: 15,
  },
  axisY2: {
    title: "Puzzle Solves",
    titleFontSize: 15,
    labelFontSize: 15,
  },
  toolTip: {
    shared: true
  },
  legend: {
    cursor: "pointer",
    verticalAlign: "top",
    horizontalAlign: "center",
    fontSize: 15,
    dockInsidePlotArea: true,
    itemclick: toogleDataSeries
  },
  data: [
    {% for line in data5_list %}
      {
        type:"line",
        axisYType: "secondary",
        name: "{{line.puzzle.puzzle_name}}",
        showInLegend: false,
        markerSize: 0,
        //yValueFormatString: "$#,###k",
        dataPoints: [
          {% for point in line.points %}
            { x: new Date("{{ point.0.isoformat }}"), y: {{point.1}} },
          {% endfor %}
        ]
      },
    {% endfor %}
  ]
};
$("#chart_div5").CanvasJSChart(options);

function toogleDataSeries(e){
  if (typeof(e.dataSeries.visible) === "undefined" || e.dataSeries.visible) {
    e.dataSeries.visible = false;
  } else{
    e.dataSeries.visible = true;
  }
  e.chart.render();
}

}
*/
