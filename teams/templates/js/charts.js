
$(document).on('ready page:load', function () {

  var randomColorGenerator = function () { 
      return '#' + (Math.random().toString(16) + '0000000').slice(2, 8); 
  };

{% for ep in solve_time %}
    var teamCanvas{{forloop.counter}} = $("canvas#chart_teams_{{forloop.counter}}");

    if (teamCanvas{{forloop.counter}}.length != 1) {
      return
    }

  new Chart(teamCanvas{{forloop.counter}}, {
      type: 'line',
      data: {
        labels: [
        {% for x in ep.names %}
        "{{x}}",
        {%endfor%}
        ],
          
        datasets: [
{% for team in ep.solve %}
          {
            label: "{{team.name}}",
            data: [
                  {% for point in team.solve %}
                  {
                  x: {{forloop.counter}},
                  y: new Date(Date.UTC({{point.year}},{{point.month}},{{point.day}},{{point.hour}},{{point.minute}},{{point.second}}))
                  },
                  {%endfor%}
                  ],
        borderColor: randomColorGenerator(),
              },
{%endfor%}
        ]
      },
      
      options: {
        scales: {
            xAxes: [{        
          type: 'time',
          time: {
            unit: 'hour',
            displayFormats: {hour: 'HH:mm'},
          },
            }]
        }
    }
      
    });

{% endfor %}


  var puzCanvas = $("canvas#chart_puz");

  if (puzCanvas.length != 1) {
    return
  }
  







new Chart(puzCanvas, {
    type: 'line',
    data: {
      labels: [
                {% for point in data_puz %}
                {{forloop.counter}},
                {%endfor%}
                ],
      datasets: [
        {
          label: "Minimum Time",
          data: [
                {% for point in data_puz %}
                {% if point.min_dur == None %}
                  null ,
                {% else %}      
                  {{point.min_dur.seconds}}/60,
                {%endif%}
                {%endfor%}
                ],
      borderColor: '#ff0000',
            },
        {
          label: "Average Time",
          data: [
                {% for point in data_puz %}
                {% if point.min_dur == None %}
                  null ,
                {% else %}      
                  {{point.av_dur.seconds}}/60,
                {%endif%}
                {%endfor%}
                ],
      borderColor: '#00ff00',
        },
      ]
    },
    
  options: {
    title: {
      display: true,
      text: 'Minimum and average resolution time per puzzle'
    }
  }
    
  });

  
});



