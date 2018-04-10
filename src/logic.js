function useURL() {
  var state = document.getElementById("url").value.length > 0;
  document.getElementById("vid").disabled = state;
  document.getElementById("pid").disabled = state;
}

function useVID() {
  var state = document.getElementById("vid").value.length > 0;
  document.getElementById("url").disabled = state;
  document.getElementById("pid").disabled = state;
  document.getElementById("radio_v").disabled = state;
  document.getElementById("radio_p").disabled = state;
}

function usePID() {
  var state = document.getElementById("pid").value.length > 0;
  document.getElementById("url").disabled = state;
  document.getElementById("vid").disabled = state;
  document.getElementById("radio_v").disabled = state;
  document.getElementById("radio_p").disabled = state;
}