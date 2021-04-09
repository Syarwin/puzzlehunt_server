function encode(message){
  return message.replace(/[\u00A0-\u9999<>\&]/g, function(i) {
   return '&#'+i.charCodeAt(0)+';';
 });
}


function message(message, type = "danger") {
  var error_msg = $('<div class="alert alert-dismissible alert-' + type + '">' + message + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>')
  error_msg.appendTo($('#guess-feedback'))//.delay(3000).fadeOut(2000, function(){$(this).remove()})
}



var guesses = [];

function addGuess(user, guess, correct, guess_uid) {
  var guesses_table = $('#guesses');
  guesses_table.prepend('<li><span class="guess-user">' + encode(user) + '</span><span class="guess-value">' + encode(guess) + '</span></li>')
  guesses.push(guess_uid)
}

function receivedNewAnswer(content) {
  if (!guesses.includes(content.guess_uid)) {
    addGuess(content.by, content.guess, content.correct, content.guess_uid)

/*
    if (content.correct) {
      var message = $('#correct-answer-message')
      var html = `"${content.guess} was correct! Taking you ${content.text}. <a class="puzzle-complete-redirect" href="${content.redirect}">go right now</a>`
      if (message.length) {
        // The server already replied so we already put up a temporary message; just update it
        message.html(html)
      } else {
        // That did not happen, so add the message
        var form = $('.form-inline')
        form.after(`<div id="correct-answer-message">${html}</div>`)
        form.remove()
      }
      setTimeout(function () {window.location.href = content.redirect}, 3000)
    }
*/
  }
}


function receivedNewHint(content) {
  message(content.hint);
}

function receivedError(content) {
  throw content.error
}


function openEventSocket() {
  const socketHandlers = {
    'new_hint': receivedNewHint,
    'new_guess': receivedNewAnswer,
    'error': receivedError,
  }

  var ws_scheme = (window.location.protocol == 'https:' ? 'wss' : 'ws') + '://'
  var sock = new WebSocket(ws_scheme + window.location.host + '/ws' + window.location.pathname)
  sock.onmessage = function(e) {
    var data = JSON.parse(e.data)
    lastUpdated = Date.now()

    if (!(data.type in socketHandlers)) {
      throw `Invalid message type: ${data.type}, content: ${data.content}`
    } else {
      var handler = socketHandlers[data.type]
      handler(data.content)
    }
  }
  sock.onerror = function() {
    //TODO this message is ugly and disappears after a while
    alert('Websocket is broken. You will not receive new information without refreshing the page.')
  }
  sock.onopen = function() {
    /*
    if (lastUpdated != undefined) {
      sock.send(JSON.stringify({'type': 'guesses-plz', 'from': lastUpdated}))
      sock.send(JSON.stringify({'type': 'hints-plz', 'from': lastUpdated}))
      sock.send(JSON.stringify({'type': 'unlocks-plz'}))
    } else {
      sock.send(JSON.stringify({'type': 'guesses-plz', 'from': 'all'}))
    }
    */
  }
}



$(function() {
  openEventSocket()

  let field = $('#answer-entry')

  $('#guess-form').submit(function(e) {
    e.preventDefault()
    if (!field.val()) {
      field.focus()
      return
    }

    var data = {
      answer: field.val(),
    }
    $.ajax({
      type: 'POST',
      url: '',
      data: $.param(data),
      contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
      /*
      success: function(data) {
        field.val('')
        fieldKeyup()
        if (data.correct == 'true') {
          correct_answer()
        } else {
          incorrect_answer(data.guess, data.timeout_length, data.timeout_end, data.unlocks)
        }
      },
      error: function(xhr, status, error) {
        button.removeData('cooldown')
        if (xhr.responseJSON && xhr.responseJSON.error == 'too fast') {
          message('Slow down there, sparky! You\'re supposed to wait 5s between guesss.', '')
        } else if (xhr.responseJSON && xhr.responseJSON.error == 'already answered') {
          message('Your team has already correctly answered this puzzle!', '')
        } else {
          message('There was an error submitting the answer.', error)
        }
      },
      */
      dataType: 'json',
    })
  })
})




/*
jQuery(document).ready(function($) {
  function is_visible(){
    var stateKey, keys = {
      hidden: "visibilitychange",
      webkitHidden: "webkitvisibilitychange",
      mozHidden: "mozvisibilitychange",
      msHidden: "msvisibilitychange"
    };
    for (stateKey in keys) {
      if (stateKey in document) {
        return !document[stateKey];
      }
    }
    return true;
  }


  // get_posts is set to be called every 3 seconds.
  // Each time get_posts does not receive any data, the time till the next call
  // gets multiplied by 2.5 until a maximum of 120 seconds, reseting to 3 when
  // get_posts receives data.
  // TODO: reset to 3 seconds when the user sends an answer
  var ajax_delay = 3;
  var ajax_timeout;

  var get_posts = function() {
    if(is_visible()){
      $.ajax({
        type: 'get',
        url: puzzle_url,
        data: {last_date: last_date},
        success: function (response) {
          var response = JSON.parse(response);
          messages = response.guess_list;
          if(messages.length > 0){
            ajax_delay = 3;
            for (var i = 0; i < messages.length; i++) {
              receiveMessage(messages[i]);
            };
            last_date = response.last_date;
          }
          else {
            ajax_delay = ajax_delay * 2.5;
            if(ajax_delay > 120){
              ajax_delay = 120;
            }
          }
        },
        error: function (html) {
          console.log(html);
          ajax_delay = ajax_delay * 2.5;
          if(ajax_delay > 120){
            ajax_delay = 120;
          }
        }
      });
    }
    ajax_timeout = setTimeout(get_posts, ajax_delay*1000);
  }

  ajax_timeout = setTimeout(get_posts, ajax_delay*1000);


  $('#sub_form').on('submit', function(e) {
    e.preventDefault();
    $("#answer_help").remove();
    $(this).removeClass("has-error");
    $(this).removeClass("has-warning");

    // Check for invalid answers:
    var non_alphabetical = /[^a-zA-Z \-_]/;
    if(non_alphabetical.test($(this).find(":text").val())) {
      $(this).append("<span class=\"help-block\" id=\"answer_help\">" +
                     "Answers will only contain the letters A-Z.</span>");
      $(this).addClass("has-error");
      return;
    }
    var spacing = /[ \-_]/;
    if(spacing.test($(this).find(":text").val())) {
      $(this).append("<span class=\"help-block\" id=\"answer_help\">" +
                     "Spacing characters are automatically removed from responses.</span>");
      $(this).addClass("has-warning");
    }
    $.ajax({
      url : $(this).attr('action') || window.location.pathname,
      type: "POST",
      data: $(this).serialize(),
      error: function (jXHR, textStatus, errorThrown) {
        if(jXHR.status == 403){
          error = "Guess rejected due to exessive guessing."
          $("<tr><td colspan = 3><i>" + error +"</i></td></tr>").prependTo("#sub_table");
        } else {
          var response = JSON.parse(jXHR.responseText);
          if("answer" in response && "message" in response["answer"][0]) {
            console.log(response["answer"][0]["message"]);
          }
        }
      },
      success: function (response) {
        clearTimeout(ajax_timeout);
        ajax_delay = 3;
        ajax_timeout = setTimeout(get_posts, ajax_delay*1000);
        response = JSON.parse(response);
        receiveMessage(response.guess_list[0]);
      }
    });
    $('#id_answer').val('');
  });

  // receive a message though the websocket from the server
  function receiveMessage(guess) {
    guess = $(guess);
    pk = guess.data('id');
    if ($('tr[data-id=' + pk + ']').length == 0) {
      guess.prependTo("#sub_table");
    } else {
      $('tr[data-id=' + pk + ']').replaceWith(guess);
    }
    if(guess.data('correct') == "True") {
      $("#id_answer").prop("disabled", true);
      $('button[type="submit"]').addClass("disabled");
      $('button[type="submit"]').attr('disabled', 'disabled');
    }
  }
});
*/
