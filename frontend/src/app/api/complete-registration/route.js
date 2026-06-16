import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

export async function POST(req) {
  try {
    const body = await req.json();

    console.log('Datos recibidos en API:', body);

    const { strava_id, email, phone, weight, height, ftp } = body;

    if (!strava_id || !email || !phone) {
      return new Response(JSON.stringify({ error: 'Faltan campos obligatorios' }), { status: 400 });
    }

    const { error } = await supabase
      .from('users')
      .update({
        email,
        telef: phone,
        weight,
        height,
        ftp,
      })
      .eq('strava_id', strava_id);

    if (error) {
      console.error('Error actualizando usuario:', error);
      return new Response(JSON.stringify({ error: 'Error en la base de datos' }), { status: 500 });
    }

    return new Response(JSON.stringify({ message: 'Registro completado correctamente' }), { status: 200 });
  } catch (e) {
    console.error('Error inesperado en API:', e);
    return new Response(JSON.stringify({ error: 'Error del servidor' }), { status: 500 });
  }
}
