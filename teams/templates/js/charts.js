


$(document).on('ready page:load', function () {



function setAllHidden(chart, hidden) {
  chart.data.datasets.forEach(function(ds) {
    ds.hidden = hidden;
  });
  chart.update()
}


  var randomColorGenerator = function () { 
      return '#' + (Math.random().toString(16) + '0000000').slice(2, 8); 
  };

{% for ep in solve_time %}
    var teamCanvas{{forloop.counter}} = $("canvas#chart_teams_{{forloop.counter}}");

    if (teamCanvas{{forloop.counter}}.length != 1) {
      return
    }

  let chart{{forloop.counter}} = new Chart(teamCanvas{{forloop.counter}}, {
      type: 'line',
      data: {
        labels: [
        {% for x in ep.names %}
        "{{x | safe}}",
        {%endfor%}
        ],
          
        datasets: [
{% for team in ep.solve %}
          {
            label: "{{team.name |truncatechars:40 }}",
            data: [
                  {% for point in team.solve %}
                  {
                  x: {{forloop.counter}},
                  y: "{{point}}"
                  },
                  {%endfor%}
                  ],
        borderColor: randomColorGenerator(),
        hidden: {% if forloop.counter < 11 %} false {%else%} true {%endif%}
              },
{%endfor%}
        ]
      },
            options: {
        scales: {
            y: {
                type: 'time',
                min: "{{ep.min}}",
                time: {
                tooltipFormat:'dd/MM HH:mm',
                        displayFormats: {
                        'millisecond':'dd/MM HH:mm',
                         'second': 'dd/MM HH:mm',
                         'minute': 'dd/MM HH:mm',
                         'hour': 'dd/MM HH:mm',
                         'day': 'dd/MM HH:mm',
                         'week': 'dd/MM HH:mm',
                         'month': 'dd/MM HH:mm',
                         'quarter': 'dd/MM HH:mm',
                         'year': 'dd/MM HH:mm',
                        },
                }
            },
            },
            
            plugins:{
            title: {
              display: true,
              text: 'Resolution times for Episode {{forloop.counter}}'
            }
    }
        }
      
      
      
      
      
    });


  let showAllButton{{forloop.counter}} = document.getElementById(`show-all-{{forloop.counter}}`)
  showAllButton{{forloop.counter}}.addEventListener('click', function() {
    setAllHidden(chart{{forloop.counter}}, false)
  })

  let hideAllButton{{forloop.counter}} = document.getElementById(`hide-all-{{forloop.counter}}`)
  hideAllButton{{forloop.counter}}.addEventListener('click', function() {
    setAllHidden(chart{{forloop.counter}}, true)
  })

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
                " {{point.name | safe}}",
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
                  "{{point.min_dur}}",
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
                  "{{point.av_dur}}",
                {%endif%}
                {%endfor%}
                ],
      borderColor: '#00ff00',
        },
        {
          label: "Median Time",
          data: [
                {% for point in data_puz %}
                {% if point.min_dur == None %}
                  null ,
                {% else %}      
                  "{{point.med_dur}}",
                {%endif%}
                {%endfor%}
                ],
      borderColor: '#0000ff',
        },
      ]
    },
    
  options: {
        
        scales: {
            y: {
                type: 'time',
                time: {
                unit: 'minute',
                tooltipFormat:'HH:mm:ss',
                        displayFormats: {
                        'millisecond':'HH:mm:ss',
                         'second': 'HH:mm:ss',
                         'minute': 'HH:mm',
                         'hour': ' HH:mm',
                         'day': 'D d HH:mm',
                         'week': 'D d HH:mm',
                         'month': 'D d m HH:mm',
                         'quarter': 'D d m HH:mm',
                         'year': 'Y d/m',
                        },
                }
            },
            },
    plugins:{
    title: {
      display: true,
      text: 'Resolution time per puzzle'
    }
    },
  }
    
  });

  
});






